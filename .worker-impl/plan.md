# Eliminate the lrn column in the erk dash TUI

## Context

The "lrn" column in the erk dash TUI table shows learn workflow status for each plan (icons like "-", "⟳", "∅", "📋 #456", "✓ #12"). This column takes up horizontal space in the already-crowded table view. The learn status information is still accessible through the plan detail screen, so the column can be removed from the table without losing functionality.

**Important clarifications:**
- This removes ONLY the "lrn" column from the plan table widget
- The Learn **view tab** (key "2") is NOT removed — it's a separate concept (filters plans by `is_learn_plan` flag)
- The learn fields in `PlanRowData` are NOT removed — they're still used by the plan detail screen
- The `LearnClicked` message and its handler in `app.py` ARE removed since there's no column to click
- The learn status display in the plan detail screen (`plan_detail_screen.py`) is KEPT

## Changes

### 1. `src/erk/tui/widgets/plan_table.py` — Remove lrn column from table

**Remove `LearnClicked` message class** (lines 60-65):
- Delete the `LearnClicked` inner class from `PlanDataTable`

**Remove `_learn_column_index` tracking**:
- Remove `self._learn_column_index: int | None = None` from `__init__` (line 89)
- Remove `self._learn_column_index = None` from `reconfigure()` (line 134)

**Remove lrn column from `_setup_columns`** (lines 203-209):
- In the `show_prs` branch: remove the two lines `self.add_column("lrn", key="learn")` and `self._learn_column_index = col_index` and `col_index += 1`
- In the `else` branch: same removal
- Both blocks that add the "lrn" column must be removed

**Remove learn cell from `_row_to_values`** (lines 295-302, 343-347):
- Remove the block computing `learn_cell` (lines 295-302)
- Remove `learn_cell` from the `values.extend(...)` calls:
  - Line 343: `values.extend([pr_display, checks_display, comments_display, learn_cell])` → `values.extend([pr_display, checks_display, comments_display])`
  - Line 345: `values.extend([checks_display, comments_display, learn_cell])` → `values.extend([checks_display, comments_display])`
  - Line 347: `values.extend([learn_cell])` → remove this line entirely (the else branch just added learn_cell)

**Remove learn column click handling from `on_click`** (lines 410-421):
- Delete the entire block that checks `self._learn_column_index` and posts `LearnClicked`

### 2. `src/erk/tui/app.py` — Remove learn click handler

**Remove `on_learn_clicked` handler** (lines 1103-1125):
- Delete the entire `on_learn_clicked` method and its `@on(PlanDataTable.LearnClicked)` decorator

**Remove the import reference** if `LearnClicked` was imported (it's referenced via `PlanDataTable.LearnClicked` so the decorator reference is the only one)

### 3. `tests/tui/test_plan_table.py` — Update tests for removed column

**Update column count assertions**:
- `test_row_to_values_basic` (line 165): count changes from 10 to 9 (remove lrn column)
- `test_row_to_values_with_prs` (line 194): count changes from 13 to 12 (remove lrn column)
- `test_row_to_values_with_runs` (line 242): count changes from 13 to 12
- `test_row_to_values_draft_pr_includes_stage` (line 547): count changes from 11 to 10
- `test_row_to_values_github_does_not_include_stage` (line 568): count changes from 10 to 9
- `test_row_to_values_with_show_pr_column_false_excludes_pr_value` (line 484): count changes from 12 to 11
- `test_row_to_values_with_show_pr_column_true_includes_pr_value` (line 522): count changes from 13 to 12

**Update column index comments and assertions**:
- `test_row_to_values_basic`: remove the `values[7]` learn assertion (line 173); local-wt moves from index 8→7, local-impl from 9→8
- `test_row_to_values_with_prs`: remove the `values[10]` learn assertion (line 204)
- `test_row_to_values_with_worktree`: worktree index changes from 8 to 7 (line 258)
- `test_expected_column_index_without_prs`: expected index changes from 8 to 7 (line 358-360, update comment)
- `test_expected_column_index_with_prs`: expected index changes from 11 to 10 (line 370-371, update comment)
- `test_expected_column_index_with_all_columns`: expected index changes from 11 to 10 (line 382-383, update comment)

**Remove learn-specific tests entirely**:
- `test_make_plan_row_with_learn_status_pending` (lines 110-114): KEEP — tests `make_plan_row` helper, not the column
- `test_make_plan_row_with_learn_status_completed_no_plan` (lines 116-120): KEEP — same reason
- `test_make_plan_row_with_learn_status_completed_with_plan` (lines 122-129): KEEP
- `test_make_plan_row_with_learn_status_plan_completed` (lines 131-143): KEEP
- `test_row_to_values_with_learn_status_clickable` (lines 294-313): DELETE — tests removed column behavior
- `test_row_to_values_with_learn_status_not_clickable` (lines 315-326): DELETE — tests removed column behavior

### 4. `tests/tui/test_app.py` — Remove learn click tests

**Delete the entire `TestOnLearnClicked` class** (lines 455-579):
- All 4 test methods test the handler that's being removed

### 5. `tests/tui/test_plan_table.py` — Column index comment updates in `TestShowPrColumnFalse`

Update the docstrings that enumerate column layouts:
- `test_row_to_values_with_show_pr_column_false_excludes_pr_value`: Remove "lrn" from the column layout comments in the docstring
- `test_row_to_values_with_show_pr_column_true_includes_pr_value`: Same

## Files NOT Changing

- **`src/erk/tui/data/types.py`**: `PlanRowData` keeps all learn fields — they're used by the plan detail screen
- **`src/erk/tui/screens/plan_detail_screen.py`**: Learn status display in the detail modal stays — it's the primary way to see learn info after the column is removed
- **`src/erk/tui/views/types.py`**: The Learn view tab (`ViewMode.LEARN`) stays — it filters plans, unrelated to the column
- **`src/erk/tui/widgets/view_bar.py`**: No changes
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`**: Data provider still computes learn fields for the detail screen
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`**: `make_plan_row` still accepts learn parameters for detail screen tests
- **`tests/tui/data/test_provider.py`**: Learn status display tests for the data provider stay
- **`tests/tui/views/test_types.py`**: Learn view config tests stay
- **`tests/tui/commands/test_execute_command.py`**: PlanRowData construction with learn fields stays
- **`tests/tui/commands/test_registry.py`**: Learn view command tests stay
- **`src/erk/tui/app.py` bindings**: The `"2"` key binding for `action_switch_view_learn` stays
- **`src/erk/tui/filtering/`**: No learn references
- **`CHANGELOG.md`**: Not modified per project rules

## Implementation Details

### Column index shifts

When the "lrn" column is removed, all columns that follow it shift left by 1. This affects `_local_wt_column_index` and `_run_id_column_index` (both computed via `col_index` counter so they auto-adjust — no manual fix needed since the counter-based approach handles this).

### Pattern: counter-based column indexing

The `_setup_columns` method uses a running `col_index` counter. Removing the `add_column("lrn", ...)` and `col_index += 1` lines causes all subsequent columns to get the correct (shifted) index automatically. No need to hardcode any new index values.

### learn_cell computation removal

The `_row_to_values` method currently computes a `learn_cell` variable with optional styling. This entire block (lines 295-302) and all references to `learn_cell` in the `values.extend(...)` calls should be removed.

### Edge case: the `else` branch at line 346-347

Currently, when `show_prs` is False, the code does `values.extend([learn_cell])`. After removal, this entire `else` block becomes empty and should be removed entirely (or the `if/else` simplified to just the `if self._plan_filters.show_prs:` branch without an else).

## Verification

1. Run `pytest tests/tui/test_plan_table.py` — all updated tests should pass with new column counts and indices
2. Run `pytest tests/tui/test_app.py` — should pass without the deleted `TestOnLearnClicked` class
3. Run `pytest tests/tui/` — full TUI test suite should pass
4. Run `ty` type checker — ensure no type errors from removed `LearnClicked` references
5. Run `ruff` linter — ensure no unused imports or dead code
6. Verify the plan detail screen still shows learn status (manual or existing tests)