# Fix `erk down -f -d` from root worktree with non-trunk branch

## Context

When a user is on a non-trunk branch in the root worktree (e.g., `unclear-what-this-is` checked out in the root repo), `erk down -f -d` fails with:

```
Error: Cannot create worktree for trunk branch "master".
```

This happens because `resolve_down_navigation` tries to create a dedicated worktree for trunk when trunk isn't currently checked out anywhere. There are three issues to fix.

## Changes

All changes in **`src/erk/cli/commands/navigation_helpers.py`**.

### 1. Simplify `resolve_down_navigation` trunk case (lines 583-597)

**Problem:** When parent is trunk and `find_worktree_for_branch("master")` returns `None` (because root has a different branch), the code tries `ensure_worktree_for_branch` which rejects creating a worktree for trunk.

**Fix:** Replace the complex trunk handling block with:
```python
if parent_branch == detected_trunk:
    return "root", False
```

Trunk always belongs in the root worktree. No need to check whether trunk is currently checked out or where.

### 2. Add `git checkout <trunk>` when navigating to root (in `execute_stack_navigation`, after line 728)

**Problem:** The activation script only does `cd` to the target path. In the standard flow each worktree already has its branch, so cd suffices. But when root has a non-trunk branch, no checkout happens.

**Fix:** After the navigation loop, when `is_root=True`, check if root worktree's branch differs from trunk. If so, build a `git checkout <trunk>` command. Use `WorktreeInfo.is_root` to find the root worktree's current branch from the `worktrees` list (already available at line 667).

- **Delete path** (line 761): Prepend checkout command before deletion_commands in `_activate_with_deferred_deletion`
- **Non-delete path** (line 775): Pass checkout command as `post_cd_commands` to `activate_target`

### 3. Skip worktree removal for root worktree in `render_deferred_deletion_commands` (lines 229-270)

**Problem:** When the current branch is in the root worktree, `get_slot_name_for_worktree` returns `None` (root is never in pool), so the code generates `git worktree remove --force <root_path>` which would try to remove the root worktree.

**Fix:** Add `is_root_worktree: bool` parameter. When `True`, skip the worktree cleanup block entirely (no `erk slot unassign`, no `git worktree remove`). Only emit branch deletion commands.

Detect root worktree using `WorktreeInfo.is_root` from the worktrees list:
```python
is_current_root_wt = any(wt.is_root and wt.path == current_worktree_path for wt in worktrees)
```

## Tests

File: **`tests/commands/navigation/test_down.py`**

### Test 1: `test_down_from_root_worktree_non_trunk_branch`

Scenario: on `feature-1` in root worktree, no dedicated worktrees, `erk down --script`.

Setup:
- Root worktree has `feature-1` (not trunk) — use manual `WorktreeInfo` list with `branch="feature-1", is_root=True`
- Graphite metadata: `main -> feature-1`
- `current_branches={env.cwd: "feature-1"}`

Assert:
- Exit code 0
- Script includes `git checkout main`
- Navigates to root repo path

### Test 2: `test_down_delete_current_from_root_worktree`

Scenario: on `feature-1` in root worktree, `erk down -d --script`, PR is merged.

Setup: same as Test 1 plus FakeGitHub with merged PR for `feature-1`.

Assert:
- Exit code 0
- Script includes `git checkout main`
- Script includes `gt delete -f --no-interactive feature-1`
- Script does NOT include `git worktree remove`

## Verification

1. Run scoped tests: `uv run pytest tests/commands/navigation/test_down.py`
2. Run ty: `uv run ty check src/erk/cli/commands/navigation_helpers.py`
3. Manual test: check out a non-trunk branch in root worktree, run `erk down -f -d`
