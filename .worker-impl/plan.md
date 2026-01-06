# Plan: Extract Deletion Helpers to Shared Module

## Summary

Extract reusable deletion helper functions from `wt/delete_cmd.py` to a new shared module `cli/commands/deletion_helpers.py`. This enables clean reuse by `branch delete` and future commands.

## Why This Refactor Is Needed

`wt/delete_cmd.py` contains helper functions that are:
- Currently `_` prefixed (private convention)
- Actually needed by other commands (e.g., upcoming `branch delete`)
- Not discoverable without reading the full 579-line file

Moving them to a shared module with good docstrings makes them:
- Explicitly public and reusable
- Self-documenting via module-level docstring
- Easy for agents to discover

## Files to Create

### `src/erk/cli/commands/deletion_helpers.py`

```python
"""Shared helpers for deletion operations across CLI commands.

This module provides reusable functions for:
- Branch deletion with Graphite awareness
- Worktree deletion (slot-aware)
- PR and plan closing
- Shell safety (escaping worktrees)

Use these helpers when implementing delete/cleanup commands.
"""
```

**Functions to move:**

| Function | Purpose |
|----------|---------|
| `delete_branch_at_error_boundary()` | Delete branch with Graphite support, proper error handling |
| `escape_worktree_if_inside()` | Change cwd if inside worktree being deleted |
| `try_git_worktree_delete()` | Attempt git worktree remove |
| `prune_worktrees_safe()` | Prune worktree metadata |
| `get_pr_info_for_branch()` | Get PR number and state |
| `close_pr_for_branch()` | Close open PR for branch |
| `get_plan_info_for_worktree()` | Get plan number and state |
| `close_plan_for_worktree()` | Close open plan for worktree |
| `delete_worktree_directory()` | Slot-aware worktree deletion |

**Note:** Remove `_` prefix when moving (they become public API).

## Files to Modify

### `src/erk/cli/commands/wt/delete_cmd.py`

1. Remove the moved functions
2. Add imports from `deletion_helpers`
3. Update all call sites to use imported functions

### `tests/commands/wt/test_delete.py` (if exists)

Update imports if tests directly reference the helper functions.

## Implementation Steps

1. Create `deletion_helpers.py` with module docstring
2. Move functions one by one, removing `_` prefix
3. Add comprehensive docstrings to each function explaining:
   - What it does
   - When to use it
   - Example usage
4. Update `wt/delete_cmd.py` imports
5. Run tests to verify no breakage

## Example Docstring Style

```python
def delete_branch_at_error_boundary(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
    force: bool,
    dry_run: bool,
    graphite: Graphite,
) -> None:
    """Delete a branch with Graphite awareness and proper error handling.

    Use this function when deleting branches that may be:
    - Tracked by Graphite (uses `gt delete`)
    - Not tracked (uses `git branch -d/-D`)

    Handles user-declined prompts gracefully (not treated as errors).

    Args:
        ctx: ErkContext with git operations
        repo_root: Repository root for branch operations
        branch: Branch name to delete
        force: Use -D (force) instead of -d
        dry_run: Print what would be done without executing
        graphite: Graphite gateway for tracking checks
    """
```

## Tests

No new tests needed - existing tests cover the functionality.
Verify existing tests pass after the refactor.