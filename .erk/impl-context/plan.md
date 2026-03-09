# Fix: `erk pr list` and `erk dash` should show same PR list

## Context

`erk pr list` shows 30 items (including learn plans), while `erk dash` PRs tab shows only 10 (excludes learn plans via `exclude_labels=("erk-learn",)`). The CLI should exclude learn plans by default to match the TUI, with a flag to include them.

## Root Cause

- **TUI** (`src/erk/tui/views/types.py:43`): PLANS_VIEW has `exclude_labels=("erk-learn",)` — filters out learn plans from PRs tab
- **CLI** (`src/erk/cli/commands/pr/list_cmd.py:302-312`): Uses `exclude_labels=()` — shows everything including learn plans

## Changes

### 1. Add `--include-learn` flag to `pr_filter_options`

**File**: `src/erk/cli/commands/pr/list_cmd.py`

Add a new option in `pr_filter_options()` (around line 85-130):
```python
f = click.option(
    "--include-learn",
    is_flag=True,
    default=False,
    help="Include learn plans in results (excluded by default)",
)(f)
```

### 2. Pass `exclude_labels` in `_pr_list_impl`

**File**: `src/erk/cli/commands/pr/list_cmd.py` — `_pr_list_impl()` (line 255)

- Accept `include_learn: bool` parameter
- Compute `exclude_labels = () if include_learn else ("erk-learn",)`
- Pass to `PlanFilters(exclude_labels=exclude_labels, ...)`

### 3. Pass `exclude_labels` in `_run_interactive_mode`

**File**: `src/erk/cli/commands/pr/list_cmd.py` — `_run_interactive_mode()` (line 352)

- Accept `include_learn: bool` parameter
- Compute `exclude_labels = () if include_learn else ("erk-learn",)`
- Pass to `PlanFilters(exclude_labels=exclude_labels, ...)`

### 4. Wire flag through `pr_list` and `dash` commands

**File**: `src/erk/cli/commands/pr/list_cmd.py`

- `pr_list()` (line 472): Accept `include_learn` kwarg, pass to `_pr_list_impl`
- `dash()` (line 520): Accept `include_learn` kwarg, pass to `_run_interactive_mode`

## Verification

1. `erk pr list` — should match TUI PRs tab count (excluding learn plans)
2. `erk pr list --include-learn` — should show all plans including learn
3. `erk dash` — unchanged behavior (already excludes learn)
4. Run existing tests: `pytest tests/unit/cli/commands/pr/ -x`
