# Plan: Retrack plan branch after plumbing commit in plan-save

## Context

When `plan-save` creates a stacked plan branch (parent is a feature branch, not trunk), the following happens:

1. `branch_manager.create_branch()` creates the branch AND calls `gt track` (Graphite records branch position A)
2. `git.commit.commit_files_to_branch()` adds the plan commit via git plumbing (branch moves to position B)
3. `git.remote.push_to_remote()` pushes position B to origin

After step 2, the branch is **diverged from Graphite's tracking** because Graphite still thinks it's at position A. If the parent branch is later rebased (e.g., via `gt submit`), the plan branch becomes unreachable from the parent's new history, and `erk br co --for-plan` fails when trying to `gt track`.

**Fix**: After `commit_files_to_branch()`, call `branch_manager.retrack_branch()` to update Graphite's tracking to include the plan commit. This keeps Graphite in sync with the actual branch state.

## Changes

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

In `_save_as_planned_pr()`, after the `git.commit.commit_files_to_branch()` call (line ~255) and before `push_to_remote`, add:

```python
    # Update Graphite tracking after plumbing commit advanced the branch
    # (create_branch tracked position A, but commit_files_to_branch moved to B)
    if not current_branch_flag:
        branch_manager.retrack_branch(repo_root, branch_name)
```

This requires adding `branch_manager = require_branch_manager(ctx)` to the existing local variables (it's already imported and used — line 177 — but currently only for `create_branch`; reuse the same variable).

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

Add a test that verifies `retrack_branch` is called after branch creation for stacked plans. Extend or add to the existing `test_planned_pr_branch_stacked_on_current_feature_branch` test to assert that `fake_graphite.retrack_branch_calls` includes the plan branch name.

## Verification

- Run existing plan-save tests to confirm no regressions
- Add new test asserting retrack is called for stacked plan branches
- Add negative test asserting retrack is NOT called for `--current-branch` mode
