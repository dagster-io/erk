# Fix: `_cleanup_no_worktree` crashes when branch is checked out in another worktree

## Context

When running `erk land` from the TUI (or root worktree), the landed branch may still be checked out in an implementation worktree. The cleanup pipeline classifies this as `NO_WORKTREE` (because you're not *in* the branch's worktree), then `_cleanup_no_worktree` tries to delete the branch without first releasing it — causing `gt delete` to fail with "currently checked out in another worktree".

The other three cleanup paths (`SLOT_ASSIGNED`, `SLOT_UNASSIGNED`, `NON_SLOT`) all call `_ensure_branch_not_checked_out()` before deletion. `_cleanup_no_worktree` is the only path that skips this defensive check.

## Fix

**File:** `src/erk/cli/commands/land_cmd.py` (line ~751)

Add `_ensure_branch_not_checked_out()` call before `delete_branch()` in `_cleanup_no_worktree`:

```python
def _cleanup_no_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup when no worktree exists: delete branch only if exists locally."""
    local_branches = cleanup.ctx.git.branch.list_local_branches(cleanup.main_repo_root)
    if cleanup.branch in local_branches:
        _ensure_branch_not_checked_out(
            cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
        )
        cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)
        user_output(click.style("✓", fg="green") + f" Deleted branch '{cleanup.branch}'")
```

## Test

**File:** `tests/unit/cli/commands/land/test_cleanup_and_navigate.py`

Add a test that sets up `worktree_path=None` (NO_WORKTREE path) but has the branch checked out in a worktree via `FakeGit`. Verify:
1. `_ensure_branch_not_checked_out` detaches HEAD in that worktree
2. Branch deletion succeeds

Follow the existing pattern from `test_cleanup_ensures_branch_not_checked_out_before_delete_with_stale_pool_state` (line 505).

## Verification

- Run existing land cleanup tests to confirm no regressions
- Run new test to confirm the fix
