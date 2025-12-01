# Plan: Handle Detached HEAD Case in erk co

## Problem

When running `erk co <branch>` and a worktree with matching name exists but is in detached HEAD state (e.g., during a rebase), the error message is confusing:

```
Error: Worktree '1745-add-check-counts-to-erk-ru-11-30-1638' already exists with different branch 'None'.
```

The `'None'` is the Python repr of `None`, not a helpful message.

## Solution

Provide a clear, actionable error message when encountering a detached HEAD worktree:

```
Error: Worktree '1745-...' is in detached HEAD state (possibly mid-rebase).

Cannot create new worktree for branch '1745-...' with same name.

Options:
  1. Resume work in existing worktree: erk wt goto 1745-...
  2. Complete or abort the rebase first, then try again
  3. Use a different branch name
```

## Implementation

### File: `src/erk/cli/commands/wt/create_cmd.py`

**Location**: Lines 177-186 in `ensure_worktree_for_branch()`

**Change**: Add explicit handling for `wt.branch is None` before the generic "different branch" error.

```python
if wt.branch != branch:
    # Detached HEAD: provide specific guidance
    if wt.branch is None:
        user_output(
            f"Error: Worktree '{name}' is in detached HEAD state "
            f"(possibly mid-rebase).\n\n"
            f"Cannot create new worktree for branch '{branch}' with same name.\n\n"
            f"Options:\n"
            f"  1. Resume work in existing worktree: erk wt goto {name}\n"
            f"  2. Complete or abort the rebase first, then try again\n"
            f"  3. Use a different branch name"
        )
        raise SystemExit(1)
    # Different branch: existing error handling
    user_output(...)
    raise SystemExit(1)
```

### Test

Add a test case in `tests/commands/test_ensure_worktree.py` to verify the detached HEAD error message is shown correctly.

## Rationale

- **Explicit over silent**: Error and stop rather than silently using the detached worktree
- **Actionable guidance**: Tell user exactly what they can do (goto, finish rebase, different name)
- **Clear diagnosis**: Mention "detached HEAD" and "possibly mid-rebase" to help user understand the state
