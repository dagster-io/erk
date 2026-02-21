# Fix: Land cleanup crashes when branch is checked out in another worktree

## Context

When landing a PR from the TUI (or any context where `worktree_path` is not provided to the land command), cleanup dispatches to `_cleanup_no_worktree()`. This function assumes no worktree has the branch checked out and directly calls `branch_manager.delete_branch()`. But the branch may still be checked out in an implementation worktree (e.g., `.claude/worktrees/planned-...`), causing `gt delete` to fail with:

```
ERROR: planned/plan-add-new-slot-flag-02-21-1401 is currently checked out in another worktree and cannot be deleted.
```

**Root cause**: `_cleanup_no_worktree()` is the **only** cleanup path that does not call `_ensure_branch_not_checked_out()` before branch deletion. The other three paths (`_cleanup_slot_with_assignment`, `_cleanup_slot_without_assignment`, `_cleanup_non_slot_worktree`) all call it defensively.

## Changes

### 1. Add defensive check to `_cleanup_no_worktree()`

**File**: `src/erk/cli/commands/land_cmd.py` (lines 747-753)

Add `_ensure_branch_not_checked_out()` before the `delete_branch()` call, consistent with all other cleanup paths:

```python
def _cleanup_no_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup when no worktree exists: delete branch only if exists locally."""
    local_branches = cleanup.ctx.git.branch.list_local_branches(cleanup.main_repo_root)
    if cleanup.branch in local_branches:
        # Defensive: ensure branch is released before deletion
        # (handles case where branch is checked out in a worktree not known to the caller,
        # e.g., landing from TUI while an implementation worktree still has the branch)
        _ensure_branch_not_checked_out(
            cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
        )
        cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)
        user_output(click.style("✓", fg="green") + f" Deleted branch '{cleanup.branch}'")
```

### 2. Add regression test

**File**: `tests/unit/cli/commands/land/test_cleanup_and_navigate.py`

Add a test that reproduces the exact scenario: `worktree_path=None` (NO_WORKTREE path) but branch is still checked out in a worktree. Verify that `_ensure_branch_not_checked_out()` detaches HEAD before deletion succeeds.

## Verification

1. Run the existing cleanup tests to verify no regressions
2. Run the new test to verify the fix
3. Scoped: `pytest tests/unit/cli/commands/land/test_cleanup_and_navigate.py`
