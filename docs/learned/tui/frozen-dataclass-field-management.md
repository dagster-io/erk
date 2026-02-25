---
title: Frozen Dataclass Field Management
read_when:
  - "removing a field from a frozen dataclass"
  - "renaming a field in PlanRowData or similar frozen dataclass"
  - "getting unexpected constructor errors after field changes"
tripwires:
  - action: "removing a field from a frozen dataclass"
    warning: "Grep for the class name across ALL constructor sites. Frozen dataclasses have 5+ places to update: field definition, real provider, fake provider, test helpers, and filtering/display logic. Missing one causes runtime TypeError."
  - action: "using positional arguments when constructing PlanRowData"
    warning: "Always use keyword arguments for frozen dataclass construction. Positional arguments break silently when fields are reordered. Use make_plan_row() helper in tests."
---

# Frozen Dataclass Field Management

Frozen dataclasses like `PlanRowData` have fields referenced across many files. Adding or removing a field requires updating every construction site, which is error-prone because the frozen constraint means you cannot incrementally update — all constructor calls must be correct simultaneously.

## The Removal Checklist

When removing a field from a frozen dataclass:

1. **Remove the field definition** from the dataclass in `data/types.py`
2. **Remove from real provider** — `RealPlanDataProvider._build_row_data()` in the plan data provider
3. **Remove from fake provider** — `FakePlanDataProvider` and the `make_plan_row()` helper in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`
4. **Remove from display logic** — `PlanDataTable._row_to_values()` in `plan_table.py`
5. **Remove from any filtering/sorting logic** that references the field
6. **Remove from documentation** — `docs/learned/tui/plan-row-data.md`

The critical step is #3 — `make_plan_row()` is used extensively in tests. Missing this causes widespread test failures.

## The Addition Checklist

Adding a field follows the same sites in reverse. See [column-addition-pattern.md](column-addition-pattern.md) for the detailed add-side pattern.

## Why Keyword Arguments Matter

PlanRowData has 47+ fields. Positional argument construction is extremely brittle:

```python
# WRONG: Positional - breaks if fields reorder
row = PlanRowData(123, None, None, None, "", ...)

# CORRECT: Keyword - survives field reordering
row = PlanRowData(plan_id=123, plan_url=None, ...)

# BEST: Use the test helper
row = make_plan_row(123, "Title", pr_number=456)
```

The `make_plan_row()` helper in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` provides sensible defaults for all fields, so tests only need to specify the fields they care about.

## Related Documentation

- [column-addition-pattern.md](column-addition-pattern.md) — the "add" side of this checklist
- [Frozen Dataclass Test Doubles](../testing/frozen-dataclass-test-doubles.md) — mutation tracking patterns for frozen fakes
- [PlanRowData Field Reference](plan-row-data.md) — complete field inventory
