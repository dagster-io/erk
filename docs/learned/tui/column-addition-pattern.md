---
title: Column Addition Pattern
read_when:
  - "adding a column to the plan table"
  - "adding a field to PlanRowData"
  - "modifying plan_table.py column layout"
tripwires:
  - action: "adding a column to PlanDataTable without updating make_plan_row"
    warning: "Column additions require 5 coordinated changes. See column-addition-pattern.md for the complete checklist."
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

Compute the display string and pass both values:

```python
created_display = format_relative_time(plan.created_at.isoformat()) or "-"
# ...
PlanRowData(
    created_at=plan.created_at,
    created_display=created_display,
)
```

### 3. Add column and value in table (`src/erk/tui/widgets/plan_table.py`)

Add the column definition and include the value in the row's values list:

```python
values: list[str | Text] = [plan_cell, Text(row.title), row.created_display]
```

Column positioning is index-based. Check filter gate conditions if the column should be conditionally visible.

### 4. Update make_plan_row in fake (`packages/erk-shared/.../plan_data_provider/fake.py`)

Add the parameter with a sentinel default:

```python
def make_plan_row(
    *,
    created_at: datetime | None = None,
    # ...
) -> PlanRowData:
    # Sentinel pattern: default to a fixed datetime
    effective_created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)
    return PlanRowData(
        created_at=effective_created_at,
        # ...
    )
```

The sentinel pattern (`created_at or datetime(2025, 1, 1, ...)`) provides a stable default for tests that don't care about the created date.

### 5. Handle serialization (`src/erk/cli/commands/exec/scripts/dash_data.py`)

Add datetime-to-string conversion for JSON serialization:

```python
for key in ("last_local_impl_at", "last_remote_impl_at", "created_at"):
    if isinstance(data[key], datetime):
        data[key] = data[key].isoformat()
```

## Checklist

| Step | File                         | Change                    |
| ---- | ---------------------------- | ------------------------- |
| 1    | `tui/data/types.py`          | Add raw + display fields  |
| 2    | `plan_data_provider/real.py` | Populate from source data |
| 3    | `tui/widgets/plan_table.py`  | Add column + value in row |
| 4    | `plan_data_provider/fake.py` | Update `make_plan_row()`  |
| 5    | `dash_data.py`               | Handle serialization      |

## Related Documentation

- [Data Contract](data-contract.md) — Display-vs-raw field duality pattern
- [PlanRowData Reference](plan-row-data.md) — Field inventory and nullable fields
