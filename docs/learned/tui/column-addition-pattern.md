---
title: Column Addition Pattern
read_when:
  - "adding a column to the plan table"
  - "adding a field to PlanRowData"
  - "modifying plan_table.py column layout"
tripwires:
  - action: "adding a column to PlanDataTable without updating make_plan_row"
    warning: "Column additions require 5 coordinated changes. See column-addition-pattern.md for the complete checklist."
last_audited: "2026-02-16 08:00 PT"
audit_result: clean
---

# Column Addition Pattern

Adding a column to the PlanDataTable requires 5 coordinated changes across the data pipeline. Missing any one causes runtime errors or test failures.

## Worked Example: created_at Datetime Column (PR #6978)

### 1. Add field to PlanRowData (`src/erk/tui/data/types.py`)

Add both the raw data field and the display-formatted field:

```python
@dataclass(frozen=True)
class PlanRowData:
    created_at: datetime     # Raw value for sorting/filtering
    created_display: str     # Formatted for display (e.g., "2d ago")
```

The raw/display duality follows the [Data Contract](data-contract.md) pattern.

### 2. Populate in real provider (`packages/erk-shared/.../plan_data_provider/real.py`)

Compute the display string and pass both values to the `PlanRowData` constructor:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, RealPlanDataProvider._build_row_data -->

See `RealPlanDataProvider._build_row_data()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` for the `created_display` and `created_at` field population.

### 3. Add column and value in table (`src/erk/tui/widgets/plan_table.py`)

Add the column definition and include the value in the row's values list.

<!-- Source: src/erk/tui/widgets/plan_table.py, PlanDataTable -->

See the `values` list construction in `PlanDataTable` in `src/erk/tui/widgets/plan_table.py`. Column positioning is index-based. Check filter gate conditions if the column should be conditionally visible.

### 4. Update make_plan_row in fake (`packages/erk-shared/.../plan_data_provider/fake.py`)

Add the parameter with a sentinel default.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py, make_plan_row -->

See `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`. Uses the sentinel pattern (`created_at or datetime(2025, 1, 1, ...)`) to provide a stable default for tests that don't care about the created date.

### 5. Handle serialization (`src/erk/cli/commands/exec/scripts/dash_data.py`)

Add datetime-to-string conversion for JSON serialization:

<!-- Source: src/erk/cli/commands/exec/scripts/dash_data.py, _serialize_plan_row -->

See `_serialize_plan_row()` in `src/erk/cli/commands/exec/scripts/dash_data.py`. Converts `datetime` fields (including `created_at`) to ISO format strings for JSON output.

## Checklist

| Node | File                         | Change                    |
| ---- | ---------------------------- | ------------------------- |
| 1    | `tui/data/types.py`          | Add raw + display fields  |
| 2    | `plan_data_provider/real.py` | Populate from source data |
| 3    | `tui/widgets/plan_table.py`  | Add column + value in row |
| 4    | `plan_data_provider/fake.py` | Update `make_plan_row()`  |
| 5    | `dash_data.py`               | Handle serialization      |

## Additional Worked Example: author Column (PR #7109)

The `author` field follows the same 5-step pattern. Unlike `created_at`, `author` has no display field (the raw string is used directly):

1. **types.py**: Added `author: str` (non-nullable, sourced from GitHub API `issue.author`)
2. **real.py**: Populated from `issue.author` in `_build_row_data()`
3. **plan_table.py**: Added column to both Plans/Learn and Objectives views
4. **fake.py**: Added `author` parameter to `make_plan_row()` with default `"test-user"`
5. **dash_data.py**: No special serialization needed (plain string)

## Related Documentation

- [Data Contract](data-contract.md) — Display-vs-raw field duality pattern
- [PlanRowData Reference](plan-row-data.md) — Field inventory and nullable fields
