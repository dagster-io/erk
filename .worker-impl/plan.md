# Eliminate the `lrn` column from the erk dash TUI

## Context

The `lrn` (learn) column in the erk dash TUI table shows the status of the "learn" workflow for each plan (e.g., `"-"`, `"⟳"`, `"∅"`, `"📋 #456"`, `"✓ #12"`). This column appears in both PLANS and LEARN views but is being removed from the table to reduce visual clutter. The learn information will remain accessible in the plan detail screen (modal), where it's already displayed.

**Scope**: Remove the `lrn` column from the table. Do NOT remove the learn data from `PlanRowData`, the fake builder, the real data provider, or the plan detail screen. The underlying learn fields remain because they're used by the detail screen and other features.

## Changes

### 1. Remove `lrn` column from `PlanDataTable._setup_columns()` in `src/erk/tui/widgets/plan_table.py`

**Lines 194-209**: Currently the `lrn` column is added in both the `show_prs` and `else` branches. Remove both `self.add_column("lrn", key="learn")` calls and the `self._learn_column_index` assignments.

Before:
```python
        if self._plan_filters.show_prs:
            if self._plan_filters.show_pr_column:
                self._pr_column_index = col_index
                self.add_column("pr", key="pr")
                col_index += 1
            self.add_column("chks", key="chks")
            col_index += 1
            self.add_column("comments", key="comments")
            col_index += 1
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
            if self._plan_filters.show_pr_column:
                self._pr_column_index = col_index
                self.add_column("pr", key="pr")
                col_index += 1
            self.add_column("chks", key="chks")
            col_index += 1
            self.add_column("comments", key="comments")
            col_index += 1
```

(The `else` branch disappears entirely since its only content was the learn column.)

### 2. Remove `_learn_column_index` instance variable from `PlanDataTable.__init__()` in `src/erk/tui/widgets/plan_table.py`

**Line 89**: Remove `self._learn_column_index: int | None = None`

### 3. Remove `_learn_column_index` reset from `PlanDataTable.reconfigure()` in `src/erk/tui/widgets/plan_table.py`

**Line 134**: Remove `self._learn_column_index = None`

### 4. Remove learn cell formatting from `PlanDataTable._row_to_values()` in `src/erk/tui/widgets/plan_table.py`

**Lines 295-302**: Remove the learn cell formatting block:
```python
        # Format learn cell - use icon-only for table, colorize if clickable
        learn_cell: str | Text = row.learn_display_icon
        if (
            row.learn_plan_issue is not None
            or row.learn_plan_pr is not None
            or row.learn_run_url is not None
        ):
            learn_cell = Text(row.learn_display_icon, style="cyan underline")
```

**Lines 343, 345, 347**: Remove `learn_cell` from the `values.extend()` calls:
- Line 343: `values.extend([pr_display, checks_display, comments_display, learn_cell])` → `values.extend([pr_display, checks_display, comments_display])`
- Line 345: `values.extend([checks_display, comments_display, learn_cell])` → `values.extend([checks_display, comments_display])`
- Line 347: `values.extend([learn_cell])` → remove this line entirely (the else branch becomes empty and can be removed)

The if/else structure around `show_prs` for building values simplifies: with the learn column gone, the `else` branch that only appended `learn_cell` disappears entirely.

### 5. Remove `LearnClicked` message class from `PlanDataTable` in `src/erk/tui/widgets/plan_table.py`

**Lines 60-65**: Remove the `LearnClicked` message class entirely.

### 6. Remove learn column click handling from `PlanDataTable._on_click()` in `src/erk/tui/widgets/plan_table.py`

**Lines 410-421**: Remove the learn column click detection block:
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

### 7. Remove `on_learn_clicked` handler from `ErkDashApp` in `src/erk/tui/app.py`

**Lines 1103-1125**: Remove the `@on(PlanDataTable.LearnClicked)` decorated handler `on_learn_clicked()` and its import reference to `PlanDataTable.LearnClicked` (the import of `PlanDataTable` itself stays since it's used for other messages).

### 8. Update tests in `tests/tui/test_plan_table.py`

**Column count assertions**: Every test that asserts `len(values)` must decrease by 1 since the `lrn` column is removed:
- `test_row_to_values_basic` (line 165): `assert len(values) == 10` → `assert len(values) == 9`
- `test_row_to_values_with_prs` (line 194): `assert len(values) == 13` → `assert len(values) == 12`
- `test_row_to_values_with_runs` (line 242): `assert len(values) == 13` → `assert len(values) == 12`

**Column index shifts**: After the learn column (previously index 7 in base layout), all subsequent column indices shift down by 1:
- `test_row_to_values_basic`: `values[7]` was learn → remove that assertion. `values[8]` was worktree → becomes `values[7]`. `values[9]` was local-impl → becomes `values[8]`.
- `test_row_to_values_with_prs`: `values[10]` was learn → remove that assertion.
- `test_row_to_values_with_worktree`: `values[8]` was worktree → becomes `values[7]`.

**Remove learn-specific tests entirely**:
- `test_row_to_values_with_learn_status_clickable` (lines 294-313): Remove entirely
- `test_row_to_values_with_learn_status_not_clickable` (lines 315-326): Remove entirely

### 9. Update tests in `tests/tui/test_app.py`

**Remove `TestOnLearnClicked` class** (around line 455): Remove the entire test class that tests learn click behavior, since the `LearnClicked` message and handler no longer exist.

### 10. Update tests in `tests/tui/commands/test_execute_command.py`

Search for any references to `learn_display_icon`, `LearnClicked`, or learn column assertions and remove them. (The explore found this file references learn but it may only be through `make_plan_row` which is unchanged.)

## Files NOT Changing

- **`src/erk/tui/data/types.py`** — `PlanRowData` keeps all `learn_*` fields. They're used by the plan detail screen.
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`** — The real provider still populates learn fields (used by detail screen).
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`** — The `make_plan_row()` builder still accepts and computes learn fields.
- **`src/erk/tui/screens/plan_detail_screen.py`** — The detail screen's learn status display stays (lines 772-789).
- **`tests/unit/cli/commands/exec/scripts/test_dash_data.py`** — Serialization tests stay; they test `PlanRowData` serialization, not column layout.
- **`tests/tui/test_plan_table.py` learn builder tests** — Tests like `test_make_plan_row_default_learn_fields`, `test_make_plan_row_with_learn_status_pending`, etc. that test `make_plan_row()` learn field computation stay unchanged (they test the data builder, not the column).
- **`src/erk/tui/views/types.py`** — View modes stay unchanged. The LEARN view still exists (it shows learn-type plans, not the learn column).
- **`packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`** — Metadata schema constants unchanged.

## Implementation Details

**Key pattern**: The `_row_to_values()` method builds a `values` list matching column order from `_setup_columns()`. Removing a column from both methods keeps them synchronized.

**Simplification opportunity**: After removing the learn column, the `if self._plan_filters.show_prs: ... else: ...` block in `_row_to_values()` (lines 335-347) simplifies because the `else` branch only appended `learn_cell`. With learn gone, the else branch is empty and should be removed entirely (along with the `if` condition, since the `show_prs` branch content should execute unconditionally only when `show_prs` is true, and nothing happens otherwise). Actually, let me reconsider: the `if show_prs` branch adds PR-related cells. Without `show_prs`, no cells are added in this section. So the if/else stays but the else body is deleted (or the else is dropped):

```python
        if self._plan_filters.show_prs:
            checks_display = _strip_rich_markup(row.checks_display)
            comments_display = _strip_rich_markup(row.comments_display)
            if self._plan_filters.show_pr_column:
                pr_display = _strip_rich_markup(row.pr_display)
                if row.pr_url:
                    pr_display = Text(pr_display, style="cyan underline")
                values.extend([pr_display, checks_display, comments_display])
            else:
                values.extend([checks_display, comments_display])
        # (no else branch needed - nothing to add when show_prs is False)
        values.extend([wt_cell, row.local_impl_display])
```

Similarly in `_setup_columns()`, with the learn column gone, the `else` branch at lines 206-209 disappears. The code becomes:

```python
        if self._plan_filters.show_prs:
            if self._plan_filters.show_pr_column:
                self._pr_column_index = col_index
                self.add_column("pr", key="pr")
                col_index += 1
            self.add_column("chks", key="chks")
            col_index += 1
            self.add_column("comments", key="comments")
            col_index += 1
        self._local_wt_column_index = col_index
```

## Verification

1. **Run tests**: `pytest tests/tui/test_plan_table.py tests/tui/test_app.py tests/tui/commands/test_execute_command.py -v` — all should pass after updates
2. **Run type checker**: `ty check src/erk/tui/widgets/plan_table.py src/erk/tui/app.py` — no type errors
3. **Grep confirmation**: `grep -r "lrn\|learn_column" src/erk/tui/widgets/plan_table.py` should return no results
4. **Grep confirmation**: `grep -r "LearnClicked" src/erk/tui/` should return no results
5. **Detail screen preserved**: `grep -r "learn_display" src/erk/tui/screens/plan_detail_screen.py` should still return results (learn info preserved in detail view)