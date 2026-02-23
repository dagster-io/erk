# Plan: Upgrade lifecycle stage to "impl" when local worktree exists

## Context

Plans #7961 and #7955 in `erk dash` show stage "planned" despite having active local worktrees and local-impl timestamps. The `compute_lifecycle_display()` function already upgrades "planned" to "implementing" when a remote workflow run exists (`has_workflow_run`), but has no equivalent for local worktree presence. This means local implementations don't reflect in the stage column until `mark-impl-started` successfully writes to GitHub, which may fail silently.

The fix: add a `has_local_worktree` parameter that triggers the same upgrade, using the `exists_locally` boolean already computed in `_build_row_data()`.

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

- Add `has_local_worktree: bool` keyword parameter to `compute_lifecycle_display()`
- Update the upgrade condition from:
  ```python
  if stage == "planned" and has_workflow_run:
  ```
  to:
  ```python
  if stage == "planned" and (has_workflow_run or has_local_worktree):
  ```
- Update docstring to mention local worktree

### 2. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Update `_compute_lifecycle_display()` wrapper (line 854) to accept and pass `has_local_worktree`
- Update the call site (line 698) to pass `has_local_worktree=exists_locally`

### 3. `tests/unit/plan_store/test_lifecycle_display.py`

- Add `has_local_worktree=False` to all ~20 existing `compute_lifecycle_display` calls
- Add 7 new tests in a "Local worktree inference tests" section:
  - planned + local worktree -> implementing
  - planned without local worktree -> stays planned
  - inferred planned (draft+OPEN) + local worktree -> implementing
  - planned + both workflow run and worktree -> implementing
  - already implementing + local worktree -> stays implementing
  - implemented + local worktree -> stays implemented (no downgrade)
  - no stage + local worktree -> returns "-"

## Files not changed

- `fake.py` - accepts pre-computed `lifecycle_display` string, never calls `compute_lifecycle_display`
- `PlanRowData` - `lifecycle_display` is already a string; upgrade happens before storage
- Status indicator functions - operate on computed display string, already handle "implementing"

## Verification

1. Run `uv run pytest tests/unit/plan_store/test_lifecycle_display.py`
2. Run `uv run pytest tests/unit/plan_store/test_draft_pr_lifecycle.py` (may also call lifecycle functions)
3. Run `erk dash` and verify plans with local worktrees show "impl" instead of "planned"
