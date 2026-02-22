# Plan: Enhance Objective View for Parallel In-Flight Status

Part of Objective #7390, Node 2.3

## Context

When multiple objective nodes are dispatched in parallel (via `--all-unblocked`), the current `erk objective view` output doesn't clearly communicate parallel activity. The `planning` status is missing from `_format_node_status()` (falls through to "pending" default), the summary only shows done/in_progress/pending (omitting planning), and the "Next node" field shows only one node even when multiple are unblocked. The TUI objectives view similarly shows only a single "next node" with no in-flight indicator.

## Changes

### 1. Add `planning` status to CLI view (`view_cmd.py`)

**File:** `src/erk/cli/commands/objective/view_cmd.py`

- Add `planning` case to `_format_node_status()`:
  ```
  if status == "planning":
      ref_text = f" plan {escape(plan)}" if plan else ""
      return f"[magenta]🚀 planning{ref_text}[/magenta]"
  ```

### 2. Enhance CLI summary section (`view_cmd.py`)

**File:** `src/erk/cli/commands/objective/view_cmd.py`

- Update "Nodes" line to include `planning` count:
  ```
  Nodes:       2/7 done, 2 planning, 1 in progress, 2 pending
  ```
- Add "In flight" line showing planning + in_progress count:
  ```
  In flight:   3
  ```
- Replace single "Next node" with "Unblocked nodes" listing ALL unblocked pending nodes:
  ```
  Next nodes:  2.3 - Update view display... (Phase 2)
               2.4 - Add integration tests... (Phase 2)
  ```
  When only one unblocked node, show singular "Next node:" (backwards compatible).

### 3. Enhance JSON output (`view_cmd.py`)

**File:** `src/erk/cli/commands/objective/view_cmd.py` — `_display_json()`

- Add `in_flight` count (planning + in_progress) to `summary` dict
- Add `pending_unblocked` list (IDs of pending unblocked nodes) to `graph` dict

### 4. Add in-flight display to TUI

**Files:**
- `src/erk/tui/data/types.py` — Add `objective_in_flight_display: str` field to `PlanRowData`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — Compute in-flight count (planning + in_progress) from summary, populate new field
- `src/erk/tui/widgets/plan_table.py` — Add "fly" column (width 3) after "prog" in objectives view, showing in-flight count or "-"
- `src/erk/tui/widgets/plan_table.py` — Update `_row_to_values()` to include new field

### 5. Show unblocked count in TUI next_node display

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- When multiple nodes are unblocked, show count prefix: `"(2) 2.1 Branch A"` instead of just `"2.1 Branch A"`
- This gives visibility into parallel opportunity without adding a column

### 6. Tests

**File:** `tests/unit/cli/commands/objective/test_view_cmd.py`

- Add `OBJECTIVE_WITH_PARALLEL_DISPATCH` fixture: fan-out with some nodes in `planning` status
- Test `planning` status emoji renders correctly (`🚀 planning`)
- Test "In flight" line appears in summary with correct count
- Test multiple unblocked nodes listed when fan-out pattern exists
- Test JSON output includes `in_flight` and `pending_unblocked` fields
- Update `test_view_objective_displays_summary` assertion to match new format (adds planning count)

**File:** `tests/fakes/plan_data_provider.py` (or equivalent)

- Update `make_plan_row()` to include new `objective_in_flight_display` field

**File:** `tests/tui/test_plan_table.py` (if needed)

- Update any objectives view tests to account for new "fly" column

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective/view_cmd.py` | Planning status, summary enhancements, JSON output |
| `src/erk/tui/data/types.py` | Add `objective_in_flight_display` field |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Compute in-flight count, unblocked count prefix |
| `src/erk/tui/widgets/plan_table.py` | Add "fly" column to objectives view |
| `tests/unit/cli/commands/objective/test_view_cmd.py` | New tests + update existing |
| `tests/fakes/plan_data_provider.py` | Update `make_plan_row()` |

## Verification

1. Run `pytest tests/unit/cli/commands/objective/test_view_cmd.py` — all tests pass
2. Run `pytest tests/tui/` — TUI tests pass
3. Manual: `erk objective view 7390` shows enhanced summary
4. Manual: Create fan-out objective with planning nodes, verify display
5. Run `make fast-ci` for full lint/format/type/test pass
