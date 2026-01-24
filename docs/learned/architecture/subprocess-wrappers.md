---
title: Subprocess Wrappers
read_when:
  - "using subprocess wrappers"
  - "executing shell commands"
  - "understanding subprocess patterns"
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations."
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

**Import**: `from erk.core.subprocess import run_subprocess_with_context`

**Behavior**: Raises `RuntimeError` with rich context on failure

**Example**:

```python
from erk.core.subprocess import run_subprocess_with_context

# ✅ CORRECT: Rich error context with stderr
result = run_subprocess_with_context(
    ["git", "worktree", "add", str(path), branch],
    operation_context=f"add worktree for branch '{branch}' at {path}",
    cwd=repo_root,
)
```

**Why use this**:

- **Rich error messages**: Includes operation context, command, exit code, stderr
- **Exception chaining**: Preserves original CalledProcessError for debugging
- **Testable**: Can be caught and handled in tests

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
    operation_context="view pull request",
    cwd=repo_root,
)
```

**Why use this**:

- **User-friendly**: Error messages are clear and actionable
- **CLI semantics**: Exits immediately with non-zero code
- **No exception handling needed**: Wrapper handles everything

## Why This Matters

- **Rich error messages**: Both wrappers include operation context, command, exit code, and stderr
- **Exception chaining**: Preserves original CalledProcessError for debugging
- **Consistent patterns**: Two clear boundaries with appropriate error handling
- **Debugging support**: Full context available in error messages and logs

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

## GitHub API Commands with Retry

For GitHub API commands that may fail due to transient network errors, use `execute_gh_command_with_retry()`:

```python
from erk_shared.subprocess_utils import execute_gh_command_with_retry

result = execute_gh_command_with_retry(cmd, cwd, time_impl)
```

This builds on `run_subprocess_with_context()` and adds:

- Automatic retry on transient errors (network timeouts, connection failures)
- Exponential backoff delays (0.5s, 1.0s by default)
- Time injection for testability

See [GitHub API Retry Mechanism](github-api-retry-mechanism.md) for the full pattern.

## Error Accumulation Pattern

When streaming stdout line-by-line with `subprocess.Popen()`, stderr must be captured in a background thread to avoid deadlock. This pattern is used in `RealClaudeExecutor.execute_command_streaming()`.

### Why Background Thread for Stderr?

The problem:

1. Process writes to both stdout and stderr
2. Main thread blocks on `for line in process.stdout`
3. If stderr buffer fills, process blocks waiting for it to drain
4. Deadlock: main thread waits for stdout, process waits for stderr

The solution:

```
Main Thread                          Background Thread
───────────────────────────────      ──────────────────────────
process = Popen(stdout=PIPE,
                stderr=PIPE)
                                     for line in process.stderr:
for line in process.stdout:              stderr_parts.append(line)
    yield parse_event(line)

process.wait()
stderr_thread.join(timeout=5.0)
# Use accumulated stderr in error msg
```

### Implementation Notes

- Use `daemon=True` so thread doesn't prevent process exit
- Use a timeout on `join()` to avoid hanging on pathological cases
- Stderr is accumulated as list, joined only when needed for error message
- See `src/erk/core/claude_executor.py` for the canonical implementation

### When to Use This Pattern

- Streaming stdout with `Popen(stdout=PIPE)` while also capturing stderr
- Long-running processes where stderr could fill its buffer
- Real-time event processing that must not block

### When NOT to Use This Pattern

- Simple `subprocess.run(capture_output=True)` - handles this automatically
- Fire-and-forget processes where stderr is ignored
- Short-lived commands that complete quickly

## Summary

- **Gateway layer**: Use `run_subprocess_with_context()` for business logic
- **CLI layer**: Use `run_with_error_reporting()` for command handlers
- **GitHub with retry**: Use `execute_gh_command_with_retry()` for network-sensitive operations
- **Streaming with stderr**: Use background thread accumulation pattern
- **Keep LBYL**: Don't migrate intentional `check=False` patterns
- **Never use bare check=True**: Always use one of the wrapper functions
