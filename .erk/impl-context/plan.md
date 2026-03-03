# Fix: Remove incorrect plnd/ skip in cleanup_impl_for_submit

## Context

PR #8414 (Feb 27) moved `.erk/impl-context/` cleanup from `setup_impl.py` (where it ran unconditionally) to `cleanup_impl_for_submit` in the submit pipeline. However, it added an incorrect skip condition: branches starting with `plnd/` skip cleanup entirely. The rationale was "plan branches where impl-context IS the PR content" — but this is wrong because **plan-save never goes through the submit pipeline**. It uses `git.remote.push_to_remote()` directly.

When `erk pr submit` or `erk exec push-and-create-pr` runs on a `plnd/` branch, it's **always** an implementation submit. The `plnd/` skip causes impl-context files to leak into every implementation PR.

## Changes

### 1. Remove plnd/ skip condition

**File**: `src/erk/cli/commands/pr/submit_pipeline.py` (line 203)

Remove the early-return block:
```python
# REMOVE these lines:
if state.branch_name.startswith(PLANNED_PR_TITLE_PREFIX):
    return state
```

The remaining guards (impl-context doesn't exist, not tracked) are sufficient.

If `PLANNED_PR_TITLE_PREFIX` is no longer used elsewhere in this file after removal, also remove the import.

### 2. Update test

**File**: `tests/unit/cli/commands/pr/submit_pipeline/test_cleanup_impl_for_submit.py`

Update `test_noop_for_plan_branch` → rename to `test_cleans_up_plan_branch` and assert that cleanup **does** happen for `plnd/` branches (removes files, creates commit).

### 3. Fix stale docstring

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

Update docstring of `cleanup_impl_for_submit` — remove the line "Skipped for plan branches (plnd/*) where impl-context IS the PR content."

## Files

- `src/erk/cli/commands/pr/submit_pipeline.py` — remove skip condition + update docstring
- `tests/unit/cli/commands/pr/submit_pipeline/test_cleanup_impl_for_submit.py` — flip test assertion

## Verification

1. `pytest tests/unit/cli/commands/pr/submit_pipeline/test_cleanup_impl_for_submit.py -x`
2. `make fast-ci`
