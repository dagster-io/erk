# Plan: Add Closed Indicator for Learn Plan Issues in TUI Dashboard

## Summary

When a learn plan issue (shown in the "lrn" column) is closed, display a closed indicator to visually distinguish it from open issues. Currently shows `📋 #5260` for all `completed_with_plan` statuses; this should show `✅ #5260` when the referenced issue is closed.

## Icon Design

| State | Current Display | New Display |
|-------|-----------------|-------------|
| `completed_with_plan` + open issue | `📋 #5260` | `📋 #5260` (unchanged) |
| `completed_with_plan` + closed issue | `📋 #5260` | `✅ #5260` |

The checkmark (✅) indicates the learn task was completed and closed.

## Implementation

### 1. Add field to PlanRowData

**File:** `src/erk/tui/data/types.py`

Add `learn_plan_issue_closed: bool | None` field to `PlanRowData`:
- `True` = issue is closed
- `False` = issue is open
- `None` = no learn plan issue or state unknown

### 2. Update display formatters

**File:** `src/erk/tui/data/provider.py`

Update `_format_learn_display()` and `_format_learn_display_icon()`:
- Add parameter `learn_plan_issue_closed: bool | None`
- When `completed_with_plan` and `learn_plan_issue_closed is True`: show `✅ #{number}`
- Otherwise keep existing `📋 #{number}` for open issues

### 3. Batch fetch learn issue states

**File:** `src/erk/tui/data/provider.py`

In `fetch_plans()`:
1. First pass: extract all `learn_plan_issue` numbers from plan bodies
2. Batch fetch issue states using `ctx.github_issues.get_issue()` for each unique number
3. Build mapping: `dict[int, bool]` (issue number -> is_closed)
4. Pass mapping to `_build_row_data()`

Note: This adds API calls but only for plans with `completed_with_plan` status. The mapping is built once per refresh.

### 4. Update _build_row_data

**File:** `src/erk/tui/data/provider.py`

- Add parameter `learn_issue_states: dict[int, bool]`
- Look up `learn_plan_issue` in the mapping to get closed state
- Pass to display formatters

### 5. Update test helper

**File:** `tests/fakes/plan_data_provider.py`

Update `make_plan_row()`:
- Add `learn_plan_issue_closed: bool | None = None` parameter
- Update display logic to use closed indicator when appropriate

## Files to Modify

1. `src/erk/tui/data/types.py` - Add field to PlanRowData
2. `src/erk/tui/data/provider.py` - Batch fetch states, update formatters
3. `tests/fakes/plan_data_provider.py` - Update test helper
4. `tests/tui/data/test_provider.py` - Add tests for closed state display

## Verification

1. Run `make fast-ci` to ensure all tests pass
2. Manual test with `erk dash -i`:
   - Find a plan with a closed learn plan issue
   - Verify it shows ✅ instead of 📋
   - Find a plan with an open learn plan issue
   - Verify it still shows 📋