# Plan: Add separate "sts" column for status indicators in TUI dashboard

## Context

The TUI dashboard's "stage" column currently combines the lifecycle stage name (e.g., "impld", "impling") with status emoji indicators (e.g., 🚀, 👀, 💥) in a single column. The user wants the status indicators split into their own "sts" column for clearer visual separation.

## Changes

### 1. Extract indicator computation into a standalone function (`lifecycle.py`)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

Add a new `compute_status_indicators()` function that returns just the emoji string (e.g., `"🚀"`, `"👀 💥"`, `""`). This extracts the indicator logic currently embedded in `format_lifecycle_with_status()`. The existing `format_lifecycle_with_status()` can then delegate to it (or be removed if no longer needed).

The new function signature:
```python
def compute_status_indicators(
    lifecycle_display: str,
    *,
    is_draft: bool | None,
    has_conflicts: bool | None,
    review_decision: str | None,
    checks_passing: bool | None,
    has_unresolved_comments: bool | None,
) -> str:
```

Returns the space-joined indicators string, or `"-"` when empty.

### 2. Add `status_display` field to `PlanRowData` (`types.py`)

**File:** `src/erk/tui/data/types.py`

Add `status_display: str` field — contains the emoji indicators (e.g., `"🚀"`, `"👀"`, `"-"`).

### 3. Populate separately in real provider (`real.py`)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Keep `lifecycle_display` as the output of `compute_lifecycle_display()` (stage name only, no indicators)
- Stop calling `format_lifecycle_with_status()` to enrich `lifecycle_display`
- Compute `status_display` via the new `compute_status_indicators()` function
- Pass both to the `PlanRowData` constructor

### 4. Add "sts" column in table (`plan_table.py`)

**File:** `src/erk/tui/widgets/plan_table.py`

In `_setup_columns()`: Add `self.add_column("sts", key="sts", width=4)` immediately after the "stage" column (before "created").

In `_row_to_values()`: Insert `row.status_display` after the stage value.

### 5. Update `make_plan_row` in fake (`fake.py`)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

Add `status_display: str = "-"` parameter and pass it through to `PlanRowData`.

### 6. Serialization (`dash_data.py`)

**File:** `src/erk/cli/commands/exec/scripts/dash_data.py`

No changes needed — `dataclasses.asdict()` automatically includes the new string field.

## Verification

1. Run `make fast-ci` to ensure all tests pass
2. Run `erk dash -i` to visually confirm the new "sts" column appears between "stage" and "created" with the emoji indicators separated from the stage name
