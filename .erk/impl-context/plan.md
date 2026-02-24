# Fix: Remove non-slot worktree after landing

## Context

When `erk land` runs from a named (non-slot) worktree, the cleanup leaves the worktree in a useless detached-HEAD state. The branch is deleted but the worktree directory persists at a detached commit. The user's shell is stuck in this dead directory with no clear way to escape. Even `erk br co master` only prints activation instructions without actually navigating.

**Root cause**: `_cleanup_non_slot_worktree()` detaches HEAD and deletes the branch, but preserves the worktree directory. Unlike slot worktrees (which have placeholder branches), non-slot worktrees have no useful state after branch deletion. Additionally, in direct execution mode, the no-op activation script points to `ctx.cwd` (the dead worktree) instead of the root repo.

## Approach

Remove the non-slot worktree directory after branch deletion, and fix the activation script to navigate to root repo.

## Changes

### 1. Update confirmation prompt (`land_cmd.py:238-242`)

Change `_gather_cleanup_confirmation` NON_SLOT case from `"(worktree preserved)"` to mention worktree removal:

```python
case CleanupType.NON_SLOT:
    assert target.worktree_path is not None
    proceed = ctx.console.confirm(
        f"After landing, delete branch '{target.branch}'"
        f" and remove worktree '{target.worktree_path.name}'?",
        default=True,
    )
```

### 2. Remove worktree in `_cleanup_non_slot_worktree()` (`land_cmd.py:805-852`)

After deleting the branch, remove the worktree directory:

- Escape process cwd out of worktree via `safe_chdir(main_repo_root)` before removal (prevents `git worktree remove` failure when cwd is inside the target)
- Call `ctx.git.worktree.remove_worktree(main_repo_root, worktree_path, force=True)`
- Prune stale worktree metadata via `ctx.git.worktree.prune_worktrees(main_repo_root)` (wrapped in try/except like `wt/delete_cmd.py:161-173`)
- Remove the now-unnecessary detached-HEAD-to-trunk-checkout logic (lines 834-852) since the worktree is being removed entirely
- Update the success message to `"Deleted branch and removed worktree '{name}'"`

### 3. Fix activation script target in `_execute_land_directly()` (`land_cmd.py:1346-1360`)

After the execution pipeline returns, determine the correct navigation target for script mode:

```python
# Determine navigation target - if worktree was removed, navigate to root
nav_target = ctx.cwd
if target.worktree_path is not None and target.is_current_branch:
    if not ctx.git.worktree.path_exists(target.worktree_path):
        nav_target = main_repo_root

if script:
    script_content = render_activation_script(
        worktree_path=nav_target,
        ...
    )
```

This is LBYL-compliant: checks filesystem state to determine navigation rather than threading a flag.

### 4. Update tests (`tests/unit/cli/commands/land/test_cleanup_and_navigate.py`)

- **`test_cleanup_and_navigate_non_slot_worktree_checkouts_trunk_before_deleting_branch` (line 318)**: Update to assert worktree IS removed (`assert non_slot_worktree_path in fake_git.removed_worktrees`). Remove assertion that worktree is NOT removed.

- **`test_cleanup_and_navigate_non_slot_worktree_checkouts_trunk_after_deleting_branch` (line 970)**: This test verifies trunk checkout after branch deletion. Since we now remove the worktree instead of checking out trunk, update this test to verify worktree removal. The trunk checkout assertions become worktree removal assertions.

- **Add test**: Non-slot worktree cleanup with `cleanup_confirmed=False` preserves both branch and worktree (existing behavior, regression test).

- **Add test**: Non-slot worktree removal calls `safe_chdir` to escape process cwd before removal.

## Files to modify

- `src/erk/cli/commands/land_cmd.py` — core fix (prompt, cleanup, navigation)
- `tests/unit/cli/commands/land/test_cleanup_and_navigate.py` — update + add tests

## Verification

1. Run existing land tests: `pytest tests/unit/cli/commands/land/`
2. Run full fast CI to check for regressions
3. Manual test: create a named worktree, land from it, verify worktree is removed and shell wrapper navigates to root
