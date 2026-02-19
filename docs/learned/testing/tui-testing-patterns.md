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

**Current parameter names:**

- `plan_id: int` (not `issue_number`)
- `plan_url: str | None` (not `issue_url`)
- `plan_body: str` (not `issue_body`)

See `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`.

## Usage Pattern

```python
from erk_shared.gateway.plan_data_provider.fake import make_plan_row

row = make_plan_row(
    plan_id=123,
    plan_url="https://github.com/owner/repo/issues/123",
    plan_body="# Implementation Plan\n...",
)
```

## When Updating Test Infrastructure

If `PlanRowData` fields change, update:

1. The dataclass definition in `types.py`
2. The `make_plan_row()` defaults in `fake.py`
3. All test files calling `make_plan_row()` with explicit kwargs
