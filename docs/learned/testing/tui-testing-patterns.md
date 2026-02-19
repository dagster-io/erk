---
title: TUI Testing Patterns
read_when:
  - "writing TUI tests"
  - "creating test plan data"
  - "using make_plan_row() factory"
---

# TUI Testing Patterns

## make_plan_row() Factory

The `make_plan_row()` factory function creates `PlanRowData` instances for testing.

Uses backend-agnostic `plan_*` parameter names (not `issue_*`).

See `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` for current parameters and defaults.

## Usage Pattern

See `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` for usage examples. The factory accepts `plan_id` as positional, with remaining parameters as keyword-only.

## When Updating Test Infrastructure

If `PlanRowData` fields change, update:

1. The dataclass definition in `types.py`
2. The `make_plan_row()` defaults in `fake.py`
3. All test files calling `make_plan_row()` with explicit kwargs
