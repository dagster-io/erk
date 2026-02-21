# Fix `erk plan list` label duplication for draft PR backend

## Context

`erk plan list` returns "No plans found matching the criteria" when `plan_backend = "draft_pr"` is configured in `~/.erk/config.toml`, even when draft PR plans exist.

The root cause is a label duplication bug in `DraftPRPlanListService`. The service prepends `_PLAN_LABEL = "erk-plan"` to the labels list it receives from the caller (`_build_plans_table`). But `_build_plans_table` already passes `["erk-plan"]` by default. The result is `["erk-plan", "erk-plan"]` being sent to GitHub's GraphQL `pullRequests(labels: ...)` filter, which uses AND semantics. GitHub's behavior with duplicate labels in this filter is undefined — it may return zero results.

`RealPlanListService` (the issue backend) passes labels directly without prepending, so it works correctly. The inconsistency between the two services causes the draft PR backend to break.

The tests expose this discrepancy: `TestDraftPRPlanListService` passes `labels=[]` while `TestPlanListService` (issue backend) passes `labels=["erk-plan"]`, because the draft PR service was designed expecting the caller to pass empty extra-labels, but production code always includes `"erk-plan"`.

## What Changes

### 1. Fix `DraftPRPlanListService.get_plan_list_data()` — `src/erk/core/services/plan_list_service.py`

Remove the `_PLAN_LABEL` prepending and the now-unused `_PLAN_LABEL` constant. Use `labels` directly, consistent with `RealPlanListService`:

```python
# Before (line 74):
all_labels = [_PLAN_LABEL, *labels]

# After:
all_labels = labels
```

Also remove the constant at line 28:
```python
# Remove this line:
_PLAN_LABEL = "erk-plan"
```

### 2. Update `TestDraftPRPlanListService` tests — `tests/unit/services/test_plan_list_service.py`

All calls to `service.get_plan_list_data(location=TEST_LOCATION, labels=[])` in `TestDraftPRPlanListService` should be updated to `labels=["erk-plan"]`. This documents the correct interface: the caller is responsible for the full labels list, not the service.

The `FakeGitHub.list_plan_prs_with_details()` ignores labels entirely, so test behavior is unchanged.

## Files to Modify

- `src/erk/core/services/plan_list_service.py` — remove `_PLAN_LABEL`, change `all_labels = [_PLAN_LABEL, *labels]` to `all_labels = labels`
- `tests/unit/services/test_plan_list_service.py` — update all `TestDraftPRPlanListService` test calls from `labels=[]` to `labels=["erk-plan"]`

## Verification

```bash
# Run targeted tests
uv run pytest tests/unit/services/test_plan_list_service.py -v

# Manual verification (requires draft_pr backend configured)
erk plan list
```

The fix is two files, ~3 lines changed in production code, plus test label updates.
