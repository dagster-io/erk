---
title: Subprocess Wrappers
read_when:
  - "using subprocess wrappers"
  - "executing shell commands"
  - "understanding subprocess patterns"
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations."
last_audited: "2026-02-07 16:34 PT"
audit_result: clean
---

# Subprocess Execution Wrappers

**NEVER use bare `subprocess.run(..., check=True)`. ALWAYS use wrapper functions.**

This guide explains the two-layer pattern for subprocess execution in erk: gateway layer and CLI layer wrappers.

## Scope

**These rules apply to production erk code** in `src/erk/` and `packages/erk-shared/`.

**Exception: erk-dev** (`packages/erk-dev/`) is developer tooling and is exempt from these rules. Direct `subprocess.run` is acceptable in erk-dev commands since they don't need the testability/dry-run benefits of wrapper functions.

## Two-Layer Pattern

Erk uses a two-layer design for subprocess execution to provide consistent error handling across different boundaries:

- **Gateway layer**: `run_subprocess_with_context()` - Raises RuntimeError for business logic
- **CLI layer**: `run_with_error_reporting()` - Prints user-friendly message and raises SystemExit

## Wrapper Functions

### run_subprocess_with_context (Gateway Layer)

**When to use**: In business logic, gateway classes, and core functionality that may be called from multiple contexts.

**Import**: `from erk_shared.subprocess_utils import run_subprocess_with_context`

**Behavior**: Raises `RuntimeError` with rich context on failure. All parameters are keyword-only.

**Example**:

```python
from erk_shared.subprocess_utils import run_subprocess_with_context

# ✅ CORRECT: Rich error context with stderr (all kwargs)
result = run_subprocess_with_context(
    cmd=["git", "worktree", "add", str(path), branch],
    operation_context=f"add worktree for branch '{branch}' at {path}",
    cwd=repo_root,
)
```

See `run_subprocess_with_context()` in `packages/erk-shared/src/erk_shared/subprocess_utils.py` for full signature and behavior.

### run_with_error_reporting (CLI Layer)

**When to use**: In CLI command handlers where you want to immediately exit on failure with a user-friendly message.

**Import**: `from erk.cli.subprocess_utils import run_with_error_reporting`

**Behavior**: Prints error message to stderr and raises `SystemExit` on failure

**Example**:

```python
from erk.cli.subprocess_utils import run_with_error_reporting

# ✅ CORRECT: User-friendly error messages + SystemExit
run_with_error_reporting(
    ["gh", "pr", "view", str(pr_number)],
    cwd=repo_root,
    error_prefix="Failed to view pull request",
)
```

See `run_with_error_reporting()` in `src/erk/cli/subprocess_utils.py` for full signature (supports `error_prefix`, `troubleshooting`, `show_output`).

## LBYL Patterns to Keep

**DO NOT migrate check=False LBYL patterns** - these are intentional:

```python
# ✅ CORRECT: Intentional LBYL pattern (keep as-is)
result = subprocess.run(cmd, check=False, capture_output=True, text=True)
if result.returncode != 0:
    return None  # Graceful degradation
```

When code explicitly uses `check=False` and checks the return code, this is a Look Before You Leap (LBYL) pattern for graceful degradation. Do not refactor these to use wrappers.

## Graceful Degradation Pattern

Not all subprocess calls should use `run_with_error_reporting()`. Use explicit exception handling when:

1. **The operation is optional** - Failure should not stop the main workflow
2. **Fire-and-forget semantics** - The result is informational, not critical
3. **Warning vs Error** - You want to show a warning and continue, not exit

### Example: Async Learn Trigger in Land Command

```python
# Pattern: check=True with explicit CalledProcessError handling
try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    # Handle success
except subprocess.CalledProcessError as e:
    # Show warning, continue execution
    user_output(click.style("⚠ ", fg="yellow") + f"Optional operation failed: {e}")
except FileNotFoundError:
    # Handle missing command gracefully
    user_output(click.style("⚠ ", fg="yellow") + "Command not found")
```

### Decision Table

| Scenario                       | Pattern                         | Reason                           |
| ------------------------------ | ------------------------------- | -------------------------------- |
| CLI command that must succeed  | `run_with_error_reporting()`    | SystemExit on failure is correct |
| Optional background operation  | Explicit exception handling     | Main operation should continue   |
| Gateway real.py implementation | `run_subprocess_with_context()` | Consistent error wrapping        |
