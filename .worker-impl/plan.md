# Infer "implementing" lifecycle stage from workflow run presence

## Context

When a plan PR has a workflow run dispatched (implement, learn, pr-address, etc.) but `mark_impl_started` hasn't yet updated the `lifecycle_stage` header, the plan still displays as "planned". The user wants: if a plan resolves to "planned" and has **any** associated workflow run, infer "implementing" instead.

## Approach

Add a `has_workflow_run: bool` keyword-only parameter to `compute_lifecycle_display()`. When the resolved stage is `"planned"` and `has_workflow_run` is True, upgrade to `"implementing"`. This keeps all lifecycle inference logic centralized in `lifecycle.py` and ensures the upgrade happens **before** `format_lifecycle_with_status()` applies draft/conflict indicators.

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

Add `*, has_workflow_run: bool` parameter to `compute_lifecycle_display()`. Insert upgrade logic after stage resolution, before color-coding:

```python
if stage == "planned" and has_workflow_run:
    stage = "implementing"
```

### 2. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Update `_compute_lifecycle_display` wrapper (line 874) to accept and forward `has_workflow_run`
- Update call site in `_build_row_data` (line 724) to pass `has_workflow_run=workflow_run is not None`

### 3. `tests/unit/plan_store/test_lifecycle_display.py`

- Update all ~15 existing `compute_lifecycle_display(plan)` calls to pass `has_workflow_run=False`
- Add new tests:
  - `test_planned_with_workflow_run_upgrades_to_implementing` — header "planned" + run → implementing
  - `test_planned_without_workflow_run_stays_planned` — header "planned" + no run → planned
  - `test_inferred_planned_with_workflow_run_upgrades_to_implementing` — draft+OPEN + run → implementing
  - `test_implementing_with_workflow_run_stays_implementing` — already implementing, no double-upgrade
  - `test_implemented_with_workflow_run_stays_implemented` — past implementing, no downgrade
  - `test_no_stage_with_workflow_run_returns_dash` — no stage + run → still dash

### No changes needed

- `format_lifecycle_with_status()` — already handles "implementing" correctly (draft/published prefix, conflict indicator)
- `fake.py` — accepts pre-formatted `lifecycle_display` strings, doesn't call `compute_lifecycle_display`
- `schemas.py` — "implementing" is already a valid `LifecycleStageValue`

## Verification

1. Run `uv run pytest tests/unit/plan_store/test_lifecycle_display.py` — all existing + new tests pass
2. Run `uv run ty check` on modified files
3. Run `uv run ruff check` on modified files
