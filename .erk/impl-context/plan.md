# Fix: Plan-save branches incorrectly stacked on current branch

## Context

When saving a plan as a draft PR, the branch is created from `current_branch` instead of trunk. This causes Graphite to track the new plan branch as a child of whatever branch you happen to be on, producing a false-positive stacked PR indicator (🥞) in the dashboard — even though the PR targets master on GitHub.

The issue-based submit flow (`submit.py:972`) already does this correctly using `origin/{trunk}`.

## Changes

### 1. Fix branch start point in `_save_as_draft_pr`

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py` (lines 173-183)

Move `detect_trunk_branch` **before** `create_branch` and use `origin/{trunk}` as the start point:

```python
# Before (buggy):
branch_manager = require_branch_manager(ctx)
current_branch = git.branch.get_current_branch(cwd)
start_point = current_branch if current_branch is not None else "HEAD"
create_result = branch_manager.create_branch(repo_root, branch_name, start_point)
...
# Detect trunk for PR base metadata
trunk = git.branch.detect_trunk_branch(cwd)

# After (fixed):
branch_manager = require_branch_manager(ctx)
trunk = git.branch.detect_trunk_branch(repo_root)
git.remote.fetch_branch(repo_root, "origin", trunk)
create_result = branch_manager.create_branch(repo_root, branch_name, f"origin/{trunk}")
```

- Remove `current_branch`/`start_point` lines (175-176)
- Move `trunk = git.branch.detect_trunk_branch(repo_root)` up (use `repo_root` not `cwd`, matching the ABC signature)
- Add `git.remote.fetch_branch()` to ensure origin/trunk is fresh (matches `submit.py:955` pattern)
- Pass `f"origin/{trunk}"` to `create_branch` — the Graphite branch manager already handles this: strips the `origin/` prefix, syncs local with remote via `_ensure_local_matches_remote`, then tracks with the local trunk name
- Remove the now-redundant `trunk = git.branch.detect_trunk_branch(cwd)` on line 183

### 2. Update test expectations

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

**`test_draft_pr_tracks_branch_with_graphite` (line 261):** Change the assertion on line 289 from `"main"` (current branch) to `"master"` (trunk branch), since the parent should now be trunk:

```python
# Before:
assert tracked_call[2] == "main"  # parent_branch (current branch used as base)

# After:
assert tracked_call[2] == "master"  # parent_branch (trunk used as base)
```

The test already sets `trunk_branches={tmp_path: "master"}` on line 265, so this validates the fix correctly.

**`test_draft_pr_trunk_branch_passes_through_to_pr_base` (line 240):** This test should continue to pass — it already asserts the PR base is "master" (the trunk), which doesn't change.

**Add new test:** `test_draft_pr_branch_not_stacked_on_current_branch` — create context where `current_branch` is a feature branch (not trunk) and verify the Graphite parent is still trunk, not the feature branch.

## Verification

1. Run `make fast-ci` (via devrun agent)
2. Specifically run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py`
3. Manual: save a plan from a non-master branch, check `gt ls` shows the new plan branch with `master` as parent
