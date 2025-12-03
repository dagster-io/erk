---
title: Subprocess Wrappers
read_when:
  - "using subprocess wrappers"
  - "executing shell commands"
  - "understanding subprocess patterns"
---

# Subprocess Execution Wrappers

**NEVER use bare `subprocess.run(..., check=True)`. ALWAYS use wrapper functions.**

This guide explains the two-layer pattern for subprocess execution in erk: integration layer and CLI layer wrappers.

## Two-Layer Pattern

Erk uses a two-layer design for subprocess execution to provide consistent error handling across different boundaries:

- **Integration layer**: `run_subprocess_with_context()` - Raises RuntimeError for business logic
- **CLI layer**: `run_with_error_reporting()` - Prints user-friendly message and raises SystemExit

## Wrapper Functions

### run_subprocess_with_context (Integration Layer)

**When to use**: In business logic, integration classes, and core functionality that may be called from multiple contexts.

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

## Summary

- **Integration layer**: Use `run_subprocess_with_context()` for business logic
- **CLI layer**: Use `run_with_error_reporting()` for command handlers
- **Keep LBYL**: Don't migrate intentional `check=False` patterns
- **Never use bare check=True**: Always use one of the wrapper functions
