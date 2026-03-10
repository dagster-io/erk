# Add PR Status Column to Runs Tab

## Context

The TUI Runs tab (`erk dash` → tab 4) shows workflow runs but doesn't display the PR's status (open, draft, merged, closed). The data is already fetched — `RunRowData.pr_state` is populated from `PullRequestInfo.state` — it's just not shown in the table.

## Plan

### 1. Add `pr_status_display` field to `RunRowData` (`src/erk/tui/data/types.py`)

Add a pre-formatted display string field (e.g., "👀", "🚧", "🎉", "⛔", or "-"):

```python
pr_status_display: str
```

### 2. Populate `pr_status_display` in `real_provider.py` (~line 348)

When building `RunRowData`, use `get_pr_status_emoji(pr_info)` from `erk_shared.gateway.github.emoji` when `pr_info` is available. Default to `"-"` when no PR info. Strip rich markup (though emojis shouldn't have any).

### 3. Add column in `run_table.py` `_setup_columns()`

Add a `"pr-st"` column (width 6) after the `pr` column. Update `_pr_column_index` tracking if needed (column indices shift).

### 4. Add value in `run_table.py` `_row_to_values()`

Include `row.pr_status_display` in the returned tuple at the correct position (after `pr_cell`).

### 5. Update `make_run_row()` test helper (`tests/fakes/tests/tui_plan_data_provider.py`)

Add `pr_status_display` parameter with default `"-"`.

## Files to Modify

- `src/erk/tui/data/types.py` — add field
- `src/erk/tui/data/real_provider.py` — populate field using `get_pr_status_emoji`
- `src/erk/tui/widgets/run_table.py` — add column + value
- `tests/fakes/tests/tui_plan_data_provider.py` — update test helper

## Verification

- Run `make fast-ci` to verify tests pass
- Run `erk dash -i` and check the Runs tab shows PR status emojis
