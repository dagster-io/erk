---
title: CLI Error Handling Anti-Patterns
read_when:
  - "handling expected CLI failures"
  - "deciding between RuntimeError and UserFacingCliError"
  - "converting exception-based error handling to UserFacingCliError"
tripwires:
  - score: 7
    action: "Using RuntimeError for expected CLI failures"
    warning: "RuntimeError is for unexpected programmer errors, NOT expected user-facing failures. Use UserFacingCliError for conditions where CLI should exit with a clear message."
    context: "RuntimeError implies a bug in the program. Expected failures (missing files, invalid input, precondition violations) should use UserFacingCliError to provide actionable error messages without stack traces."
---

# CLI Error Handling Anti-Patterns

## The Problem: RuntimeError for Expected Failures

`RuntimeError` is a Python built-in for **unexpected** runtime failures - conditions that indicate a bug in the program logic. Using it for **expected** CLI failures (user errors, missing preconditions, invalid state) is an anti-pattern because:

1. **Wrong semantic**: RuntimeError implies programmer error, not user error
2. **Poor UX**: Stack traces for expected failures confuse users
3. **Hard to catch**: Generic exceptions make targeted error handling difficult
4. **Missing context**: RuntimeError doesn't carry structured failure information

## The Solution: UserFacingCliError

Use `UserFacingCliError` for expected CLI failures:

```python
from erk.core.user_facing_cli_error import UserFacingCliError

# WRONG: RuntimeError for expected failure
def get_plan_folder() -> Path:
    impl_path = Path(".impl")
    if not impl_path.exists():
        raise RuntimeError("No .impl/ folder found in current directory")
    return impl_path

# CORRECT: UserFacingCliError with actionable message
def get_plan_folder() -> Path:
    impl_path = Path(".impl")
    if not impl_path.exists():
        raise UserFacingCliError(
            "No .impl/ folder found in current directory",
            hint="Run 'erk plan-implement' to set up an implementation environment",
        )
    return impl_path
```

## When to Use Each

| Exception Type       | Use Case                      | Example                                                |
| -------------------- | ----------------------------- | ------------------------------------------------------ |
| `UserFacingCliError` | Expected user-facing failures | Missing config, invalid input, precondition violations |
| `RuntimeError`       | Unexpected internal failures  | Assertion violations, impossible states, logic bugs    |
| Domain exceptions    | Operation-specific failures   | `GitOperationError`, `GatewayError` (for internal use) |

## Migration Pattern

PR #6353 shows the migration pattern from RuntimeError to UserFacingCliError:

**Before:**

```python
if not branch_name:
    raise RuntimeError("Branch name is required")
```

**After:**

```python
if not branch_name:
    raise UserFacingCliError(
        "Branch name is required",
        hint="Specify branch with --branch flag or ensure current worktree has a branch",
    )
```

**Key improvements:**

1. Clear exception type signals expected failure
2. Hint provides actionable next steps
3. No confusing stack trace for users
4. Exception can be caught by type for specific handling

## Current State

As of PR #6353:

- 8 files converted from RuntimeError to UserFacingCliError
- 47 files still contain RuntimeError instances (not all are anti-patterns)
- Ongoing migration: Convert RuntimeError → UserFacingCliError when editing affected code

## Identifying Anti-Patterns

RuntimeError is an anti-pattern when:

1. **User input validation**: Checking CLI arguments, file paths, configuration
2. **Precondition checks**: Verifying required state before operations
3. **Expected failure modes**: Missing files, network errors, permission issues

RuntimeError is appropriate when:

1. **Assertion failures**: Internal invariants violated (use `assert` with RuntimeError)
2. **Impossible states**: Logic branches that should never execute
3. **Development errors**: Configuration mistakes by developers (not users)

## Related Patterns

- [UserFacingCliError](../architecture/user-facing-cli-error.md) - Exception design and usage
- [CLI Development](cli-development.md) - CLI command design patterns
- [Error Handling](../architecture/error-handling.md) - Comprehensive error handling guide

## Attribution

Anti-pattern documented from PR #6353 investigation (Issue #6335).
