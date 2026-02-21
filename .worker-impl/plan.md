# Eliminate the lrn column in the erk dash TUI

## Context

The `erk dash` TUI plan table currently displays a "lrn" column that shows the learn workflow status for each plan (icons like "-", "⟳", "∅", "#456", "✓ #12"). This column takes up horizontal space in the already-crowded table. The learn status is still available in the plan detail screen (opened with Space), so removing it from the table improves density without losing access to the information.

**Scope**: Remove only the "lrn" **column** from the `PlanDataTable`. Do NOT remove:
- The Learn **view** (`ViewMode.LEARN`) — this stays
- The learn-related fields on `PlanRowData` — these stay (used by plan detail screen)
- The learn section in `PlanDetailScreen` — this stays
- The learn data population in `RealPlanDataProvider` or `make_plan_row` — these stay

## Changes

### 1. `src/erk/tui/widgets/plan_table.py` — Remove lrn column and click handler

**Remove the `LearnClicked` message class** (lines 60-65):
```python
class LearnClicked(Message):
    """Posted when user clicks learn column on a row with a learn plan issue or PR."""
    def __init__(self, row_index: int) -> None:
        super().__init__()
        self.row_index = row_index
```

**Remove `_learn_column_index` tracking**:
- Remove `self._learn_column_index: int | None = None` from `__init__` (line 89)
- Remove `self._learn_column_index = None` from `reconfigure()` (line 134)

**Remove lrn column from `_setup_columns()`** (lines 203-209):
- In the `show_prs` branch: remove `self.add_column("lrn", key="learn")` and `self._learn_column_index = col_index` and `col_index += 1`
- In the `else` branch: remove `self.add_column("lrn", key="learn")` and `self._learn_column_index = col_index` and `col_index += 1`

The `_local_wt_column_index` assignment stays — it just shifts down by 1 since there's one fewer column before it.

**Remove learn_cell from `_row_to_values()`** (lines 295-302, 343-347):
- Remove the entire `learn_cell` construction block:
  ```python
  learn_cell: str | Text = row.learn_display_icon
  if (
      row.learn_plan_issue is not None
      or row.learn_plan_pr is not None
      or row.learn_run_url is not None
  ):
      learn_cell = Text(row.learn_display_icon, style="cyan underline")
  ```
- In `show_prs` branch: change `values.extend([pr_display, checks_display, comments_display, learn_cell])` → `values.extend([pr_display, checks_display, comments_display])`
- In `show_prs` without pr_column branch: change `values.extend([checks_display, comments_display, learn_cell])` → `values.extend([checks_display, comments_display])`
- Remove the `else` branch that adds `learn_cell`: `values.extend([learn_cell])` → (remove entirely, or replace with empty `pass` if needed for syntax, but the structure should be: if show_prs adds pr-related values, else adds nothing before local-wt)

After removing the else-only-adds-learn_cell, the if/else structure for show_prs simplifies. With learn_cell gone from both branches, the `else` branch is empty and can be removed — just move `values.extend([wt_cell, row.local_impl_display])` directly after the if block.

**Remove learn column click handler from `on_click()`** (lines 410-421):
Remove the entire block:
```python
# Check learn column - post event if learn plan issue, PR, or run URL exists
if self._learn_column_index is not None and col_index == self._learn_column_index:
    row = self._rows[row_index] if row_index < len(self._rows) else None
    if row is not None and (
        row.learn_plan_issue is not None
        or row.learn_plan_pr is not None
        or row.learn_run_url is not None
    ):
        self.post_message(self.LearnClicked(row_index))
        event.prevent_default()
        event.stop()
        return
```

### 2. `src/erk/tui/app.py` — Remove LearnClicked event handler

**Remove the `on_learn_clicked` method** (lines 1103-1125):
```python
@on(PlanDataTable.LearnClicked)
def on_learn_clicked(self, event: PlanDataTable.LearnClicked) -> None:
    ...
```

Remove the entire method including the `@on(PlanDataTable.LearnClicked)` decorator.

### 3. `tests/tui/test_plan_table.py` — Update column counts and indices

**Update `TestPlanRowData` tests** — remove learn-specific tests:
- Remove `test_make_plan_row_with_learn_status_pending` (lines ~110-114)
- Remove `test_make_plan_row_with_learn_status_completed_no_plan` (lines ~116-120)
- Remove `test_make_plan_row_with_learn_status_completed_with_plan` (lines ~122-129)
- Remove `test_make_plan_row_with_learn_status_plan_completed` (lines ~131-139)

Wait — these test `make_plan_row` itself, not the column. Since `make_plan_row` and the learn fields on `PlanRowData` are NOT being removed, these tests should stay. The fields are still used by the plan detail screen.

**Update `TestPlanDataTableRowConversion` tests** — adjust column counts and indices:

- `test_row_to_values_basic`: Change `assert len(values) == 10` → `assert len(values) == 9`. Remove the learn assertion at index 7. Shift worktree to index 7, local-impl to index 8.
- `test_row_to_values_with_prs`: Change `assert len(values) == 13` → `assert len(values) == 12`. Remove learn assertion at index 10.
- `test_row_to_values_with_runs`: Change `assert len(values) == 13` → `assert len(values) == 12`.
- `test_row_to_values_with_worktree`: Change worktree index from 8 to 7.

**Update `TestLocalWtColumnIndex` tests** — shift expected indices:
- `test_expected_column_index_without_prs`: Change expected from 8 to 7. Update comment.
- `test_expected_column_index_with_prs`: Change expected from 11 to 10. Update comment.
- `test_expected_column_index_with_all_columns`: Change expected from 11 to 10. Update comment.

**Update `TestShowPrColumnFalse` tests**:
- `test_row_to_values_with_show_pr_column_false_excludes_pr_value`: Change `assert len(values) == 12` → `assert len(values) == 11`.
- `test_row_to_values_with_show_pr_column_true_includes_pr_value`: Change `assert len(values) == 13` → `assert len(values) == 12`.

**Update stage column tests**:
- `test_row_to_values_draft_pr_includes_stage`: Change `assert len(values) == 11` → `assert len(values) == 10`. Update comment.
- `test_row_to_values_github_does_not_include_stage`: Change `assert len(values) == 10` → `assert len(values) == 9`. Update comment.

**Update all column-listing comments** throughout the test file to remove "lrn" from the column sequence.

### 4. `tests/tui/test_app.py` — Remove `TestOnLearnClicked` test class

Remove the entire `TestOnLearnClicked` class (lines ~455-579) containing:
- `test_learn_click_opens_pr_when_both_pr_and_issue_set`
- `test_learn_click_opens_issue_when_only_issue_set`
- `test_learn_click_does_nothing_when_no_learn_data`
- `test_learn_click_does_nothing_when_no_issue_url`

## Files NOT changing

- `src/erk/tui/data/types.py` — `PlanRowData` fields for learn stay (used by plan detail screen)
- `src/erk/tui/screens/plan_detail_screen.py` — Learn section in detail screen stays
- `src/erk/tui/views/types.py` — `ViewMode.LEARN` and `LEARN_VIEW` stay
- `src/erk/tui/commands/registry.py` — No changes needed
- `src/erk/tui/widgets/view_bar.py` — Still shows Learn view tab
- `src/erk/tui/screens/help_screen.py` — Still shows "2 Learn view" help binding
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — Learn data population stays
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` — `make_plan_row` learn params stay
- `src/erk/cli/commands/exec/scripts/dash_data.py` — No learn references exist here
- `tests/tui/test_plan_table.py` `TestPlanRowData` learn tests — These test `make_plan_row` which stays
- `tests/tui/data/test_provider.py` — Tests learn_display_icon computation in the provider, stays
- `tests/tui/commands/test_execute_command.py` — Uses learn_display_icon in make_plan_row calls, stays
- `tests/unit/cli/commands/exec/scripts/test_dash_data.py` — Uses learn_display_icon in make_plan_row calls, stays

## Implementation Details

### Column index arithmetic

After removing the lrn column, every column that previously came after lrn shifts down by 1. This affects:
- `_local_wt_column_index` — computed dynamically via `col_index`, so it auto-adjusts
- `_run_id_column_index` — same, auto-adjusts
- `_stage_column_index` — comes before where lrn was, so unaffected

The key insight is that `_setup_columns()` uses an incrementing `col_index` counter, so removing the lrn `add_column` + `col_index += 1` lines automatically shifts all subsequent column indices correctly. No manual index fixup is needed in the source code.

### Simplifying the show_prs branching

Currently the code has:
```python
if self._plan_filters.show_prs:
    ...
    values.extend([..., learn_cell])
else:
    values.extend([learn_cell])
```

After removing learn_cell, the `else` branch becomes empty. The code simplifies to:
```python
if self._plan_filters.show_prs:
    ...
    values.extend([pr_display, checks_display, comments_display])
# No else needed — learn_cell was the only thing there
values.extend([wt_cell, row.local_impl_display])
```

## Verification

1. Run `make ty` — type checking should pass
2. Run `pytest tests/tui/test_plan_table.py` — updated column count tests pass
3. Run `pytest tests/tui/test_app.py` — LearnClicked tests removed, remaining tests pass
4. Run `pytest tests/tui/` — full TUI test suite passes
5. Run `make test-fast` — all unit tests pass