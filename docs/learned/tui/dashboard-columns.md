---
title: Dashboard Column Inventory
read_when:
  - "adding a new column to the erk dash TUI"
  - "understanding which columns are always present vs conditional"
  - "debugging why a column is missing in a particular view mode"
tripwires:
  - action: "adding stage column outside draft_pr backend check"
    warning: "stage column is draft_pr-only. It appears before obj in the column order. Check _setup_columns() for the backend conditional block."
---

# Dashboard Column Inventory

The `erk dash` TUI uses `PlanDataTable` (`src/erk/tui/widgets/plan_table.py`) for its column layout. Column presence depends on the active view mode and plan backend.

## Plans View Columns (Default)

Column order in `_setup_columns()` for `ViewMode.PLANS`:

| Column Header  | Key           | Width | Condition                                         |
| -------------- | ------------- | ----- | ------------------------------------------------- |
| `plan` or `pr` | `plan`        | 6     | Always (header is `pr` in draft_pr mode)          |
| `stage`        | `stage`       | 9     | Only when `plan_backend == "draft_pr"`            |
| `sts`          | `status`      | —     | Always                                            |
| `created`      | `created`     | 7     | In draft_pr mode (positioned here, not after run) |
| `obj`          | `objective`   | 5     | Always                                            |
| `loc`          | `location`    | 3     | Always (location emoji)                           |
| `branch`       | `branch`      | 42    | Always                                            |
| `run-id`       | `run_id`      | 10    | Always                                            |
| `run`          | `run_state`   | 3     | Always (run state emoji)                          |
| `created`      | `created`     | 7     | Only when NOT draft_pr (positioned after run)     |
| `author`       | `author`      | 9     | Always                                            |
| `pr`           | `pr`          | 8     | Only when `show_prs` and `show_pr_column` enabled |
| `chks`         | `chks`        | 8     | Only when `show_prs` enabled                      |
| `cmts`         | `comments`    | 5     | Only when `show_prs` enabled                      |
| `local-wt`     | `local_wt`    | 14    | Always                                            |
| `local-impl`   | `local_impl`  | 10    | Always                                            |
| `remote-impl`  | `remote_impl` | 10    | Only when `show_runs` enabled                     |

The `stage` column shows lifecycle abbreviations from `compute_lifecycle_display()` (9-char width drives abbreviations like "impling" and "impld"). PR status indicators (draft, published, conflicts, review decisions) are rendered inline within the stage column by `format_lifecycle_with_status()`.

## Objectives View Columns

When `ViewMode.OBJECTIVES` is active, an entirely different column set is used:

| Column Header  | Key         | Width | Purpose                       |
| -------------- | ----------- | ----- | ----------------------------- |
| `plan` or `pr` | `plan`      | 6     | Objective number              |
| `obj`          | `objective` | 5     | Objective identifier          |
| `prog`         | `progress`  | 5     | Completion progress           |
| `next node`    | `next_node` | 30    | Recommended next roadmap node |
| `deps`         | `deps`      | 12    | Dependency status             |
| `updated`      | `updated`   | 7     | Last update time              |
| `author`       | `author`    | 9     | Creator                       |

## Backend-Conditional Columns

Two columns behave differently based on `plan_backend`:

1. **`plan`/`pr` column**: Shows `plan` header for issue-based backend, `pr` header for `draft_pr` backend (since in draft_pr mode, the plan IS the PR).
2. **`stage` column**: Only added in `draft_pr` mode — shows the lifecycle stage with inline PR status indicators (planned, impling, impld, merged, closed).
3. **`created` column**: Present in both modes, but positioned differently — after `stage` in draft_pr mode, after `run` in issue mode.

## Adding a New Column

Follow the pattern documented in [column-addition-pattern.md](column-addition-pattern.md):

1. Add field to `PlanRowData` in `data/types.py`
2. Populate it in `RealPlanDataProvider._build_row_data()`
3. Add column in `PlanDataTable._setup_columns()` with appropriate condition
4. Add value in `PlanDataTable._row_to_values()`
5. Update `make_plan_row()` test helper

## Code Location

<!-- Source: src/erk/tui/widgets/plan_table.py, _setup_columns -->

`src/erk/tui/widgets/plan_table.py` — `_setup_columns()` method, lines ~147–220.
