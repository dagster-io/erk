# Eliminate the `lrn` Column from the Erk Dash TUI

## Context

The `lrn` (learn) column in the `erk dash` TUI table displays the learn workflow status for each plan (e.g., "not started", "in progress", issue/PR links). This column adds visual clutter to the already wide table. The learn status information is still accessible in the plan detail screen (shown when pressing Enter on a row), so removing the column from the table does not lose any functionality.

**Important clarification**: This task removes only the `lrn` **column** from the table. It does NOT remove:
- The Learn **view** (ViewMode.LEARN, key binding `2`)
- The learn status display in the plan detail screen
- Any learn-related data fields from `PlanRowData`
- Any learn-related click handling in `app.py`
- The `is_learn_plan` field or learn view filtering

## Changes

### 1. `src/erk/tui/widgets/plan_table.py` - Remove `lrn` column and related click handling

**Remove the `LearnClicked` message class** (lines 60-65):
```python
# DELETE this entire class
class LearnClicked(Message):
    """Posted when user clicks learn column on a row with a learn plan issue or PR."""
    def __init__(self, row_index: int) -> None:
        super().__init__()
        self.row_index = row_index
```

**Remove `_learn_column_index` tracking** from `__init__` (line 89):
```python
# DELETE this line
self._learn_column_index: int | None = None
```

**Remove `_learn_column_index` reset** from `reconfigure` (line 134):
```python
# DELETE this line
self._learn_column_index = None
```

**Remove `lrn` column from `_setup_columns`** (lines 203-209): Remove both `self.add_column("lrn", key="learn")` calls and the `self._learn_column_index = col_index` assignments. The `if self._plan_filters.show_prs:` / `else:` block structure changes:

Before:
```python
if self._plan_filters.show_prs:
    ...
    self.add_column("lrn", key="learn")
    self._learn_column_index = col_index
    col_index += 1
else:
    self.add_column("lrn", key="learn")
    self._learn_column_index = col_index
    col_index += 1
```

After:
```python
if self._plan_filters.show_prs:
    ...
    # lrn column removed - no else branch needed anymore
```

The `else` branch previously only added the `lrn` column. With `lrn` removed, the `else` branch is empty and should be deleted entirely. The code should flow directly from the `if self._plan_filters.show_prs:` block (without `lrn`) to the `self._local_wt_column_index = col_index` line.

**Remove learn cell formatting from `_row_to_values`** (lines 295-302): Remove the `learn_cell` variable computation and its usage. Specifically:
- Delete the `learn_cell` variable and its conditional logic (lines 296-302)
- In the `show_prs` branch, remove `learn_cell` from the `values.extend(...)` calls:
  - Line 343: `values.extend([pr_display, checks_display, comments_display, learn_cell])` -> `values.extend([pr_display, checks_display, comments_display])`
  - Line 345: `values.extend([checks_display, comments_display, learn_cell])` -> `values.extend([checks_display, comments_display])`
- Delete the `else` branch that only appends `learn_cell` (lines 346-347):
  ```python
  # DELETE
  else:
      values.extend([learn_cell])
  ```

**Remove learn column click handling** from `on_click` (lines 410-421): Delete the entire `# Check learn column` block.

### 2. `src/erk/tui/app.py` - Remove `on_learn_clicked` handler

**Remove the `on_learn_clicked` method and its decorator** (lines 1103-1125):
```python
# DELETE this entire method
@on(PlanDataTable.LearnClicked)
def on_learn_clicked(self, event: PlanDataTable.LearnClicked) -> None:
    ...
```

The `LearnClicked` import is implicit through `PlanDataTable` so no import changes needed.

### 3. `tests/tui/test_plan_table.py` - Update tests

**Remove learn-specific column tests**:
- `test_make_plan_row_with_learn_status_pending` (line 110)
- `test_make_plan_row_with_learn_status_completed_no_plan` (line 116)
- `test_make_plan_row_with_learn_status_completed_with_plan` (line 122)
- `test_make_plan_row_with_learn_status_plan_completed` (line 131)
- `test_row_to_values_with_learn_status_clickable` (line 294)
- `test_row_to_values_with_learn_status_not_clickable` (line 315)

**Update column index assertions** in remaining tests. With `lrn` column removed, column indices shift. For the Plans view (no PRs, no runs):
- Old order: plan(0), obj(1), sts(2), title(3), branch(4), created(5), author(6), **lrn(7)**, local-wt(8), local-impl(9)
- New order: plan(0), obj(1), sts(2), title(3), branch(4), created(5), author(6), local-wt(7), local-impl(8)

For the Plans view (with PRs):
- Old order: ...author(6), pr(7), chks(8), comments(9), **lrn(10)**, local-wt(11), local-impl(12)
- New order: ...author(6), pr(7), chks(8), comments(9), local-wt(10), local-impl(11)

Update any test that asserts `values[7]` is learn to check that `values[7]` is now local-wt, etc. Specifically:
- Line 173: `assert _text_to_str(values[7]) == "-"  # learn` -> delete or re-index for local-wt
- Line 174: `assert _text_to_str(values[8]) == "-"  # worktree` -> becomes `values[7]`
- Line 175: `assert _text_to_str(values[9]) == "-"  # local impl` -> becomes `values[8]`
- Line 204: `assert _text_to_str(values[10]) == "-"  # learn` -> delete this assertion (PR mode)

Read the full test file during implementation to catch all index-dependent assertions.

### 4. `tests/tui/test_app.py` - Remove learn click tests

**Remove the entire `TestOnLearnClicked` class** (starts at line 455). This class tests `on_learn_clicked` which is being removed:
- `test_learn_click_opens_pr_when_both_pr_and_issue_set`
- `test_learn_click_opens_issue_when_only_issue_set`
- `test_learn_click_does_nothing_when_no_learn_data`
- `test_learn_click_does_nothing_when_no_issue_url`

### 5. `src/erk/tui/screens/plan_detail_screen.py` - NO CHANGES

The plan detail screen's "Learn" row (lines 772-789) should be **kept**. This is where users can still see learn status when they open a plan's detail view. The detail screen is NOT part of the table column being eliminated.

### 6. Files NOT changing

- `src/erk/tui/data/types.py` - `PlanRowData` fields stay (learn data still used by detail screen)
- `src/erk/tui/views/types.py` - `ViewMode.LEARN` and `LEARN_VIEW` stay (Learn view is separate from the column)
- `src/erk/tui/app.py` `_filter_rows_for_view` - Learn view filtering stays
- `src/erk/tui/app.py` `action_switch_view_learn` - Key binding stays
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` - Data fetching stays
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` - `make_plan_row` stays (learn params still used for detail screen tests)
- `src/erk/tui/widgets/status_bar.py` - No learn column references
- `src/erk/tui/sorting/logic.py` - No learn column references
- `src/erk/tui/filtering/logic.py` - No learn column references
- `src/erk/cli/commands/exec/scripts/dash_data.py` - JSON serialization stays

## Implementation Order

1. Remove `lrn` column from `plan_table.py` (`_setup_columns`, `_row_to_values`, `on_click`, `LearnClicked` message, `_learn_column_index`)
2. Remove `on_learn_clicked` handler from `app.py`
3. Update `tests/tui/test_plan_table.py` - remove learn tests, fix column indices
4. Update `tests/tui/test_app.py` - remove `TestOnLearnClicked` class

## Verification

1. Run `pytest tests/tui/test_plan_table.py -x` - all tests pass with updated indices
2. Run `pytest tests/tui/test_app.py -x` - all tests pass without learn click tests
3. Run `pytest tests/tui/ -x` - full TUI test suite passes
4. Run `ty` - no type errors
5. Run `ruff check src/erk/tui/` - no lint errors