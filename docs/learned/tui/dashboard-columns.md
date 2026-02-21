---
title: Dashboard Column Inventory
read_when:
  - "adding a new column to the erk dash TUI"
  - "understanding which columns are always present vs conditional"
  - "debugging why a column is missing in a particular view mode"
---

# Dashboard Column Inventory

The `erk dash` TUI uses `PlanDataTable` (`src/erk/tui/widgets/plan_table.py`) for its column layout. Column presence depends on the active view mode and plan backend.

## Plans View Columns (Default)

These columns appear in the standard plans view (`ViewMode.PLANS`):

| Column Header  | Key           | Always Present | Condition                                             |
| -------------- | ------------- | -------------- | ----------------------------------------------------- |
| `plan` or `pr` | `plan`        | Yes            | Header is `pr` in draft_pr mode, `plan` otherwise     |
| `obj`          | `objective`   | Yes            | Always                                                |
| `sts`          | `status`      | Yes            | Always                                                |
| `title`        | `title`       | Yes            | Always                                                |
| `branch`       | `branch`      | Yes            | Always (added in PR #7701)                            |
| `created`      | `created`     | Yes            | Always                                                |
| `author`       | `author`      | Yes            | Always                                                |
| `stage`        | `stage`       | No             | Only when `plan_backend == "draft_pr"`                |
| `pr`           | `pr`          | No             | Only when `show_prs` and `show_pr_column` are enabled |
| `chks`         | `chks`        | No             | Only when `show_prs` is enabled                       |
| `comments`     | `comments`    | No             | Only when `show_prs` is enabled                       |
| `lrn`          | `learn`       | Yes            | Always                                                |
| `local-wt`     | `local_wt`    | Yes            | Always                                                |
| `local-impl`   | `local_impl`  | Yes            | Always                                                |
| `remote-impl`  | `remote_impl` | No             | Only when `show_runs` is enabled                      |
| `run-id`       | `run_id`      | No             | Only when `show_runs` is enabled                      |
| `run-state`    | `run_state`   | No             | Only when `show_runs` is enabled                      |

## Objectives View Columns

When `ViewMode.OBJECTIVES` is active, an entirely different column set is used:

| Column Header  | Key         | Purpose                       |
| -------------- | ----------- | ----------------------------- |
| `plan` or `pr` | `plan`      | Objective number              |
| `obj`          | `objective` | (reserved)                    |
| `title`        | `title`     | Objective title               |
| `prog`         | `progress`  | Completion progress           |
| `next node`    | `next_node` | Recommended next roadmap node |
| `deps`         | `deps`      | Dependency count              |
| `updated`      | `updated`   | Last update time              |
| `author`       | `author`    | Creator                       |

## Backend-Conditional Columns

Two columns behave differently based on `plan_backend`:

1. **`plan`/`pr` column**: Shows `plan` header for issue-based backend, `pr` header for `draft_pr` backend (since in draft_pr mode, the plan IS the PR).
2. **`stage` column**: Only added in `draft_pr` mode — shows the lifecycle stage (planned, implementing, implemented, etc.).

## Adding a New Column

Follow the pattern documented in `src/erk/tui/AGENTS.md`:

1. Add field to `PlanRowData` in `data/types.py`
2. Populate it in `RealPlanDataProvider._build_row_data()`
3. Add column in `PlanDataTable._setup_columns()` with appropriate condition
4. Add value in `PlanDataTable._row_to_values()`
5. Update `make_plan_row()` test helper

## Code Location

`src/erk/tui/widgets/plan_table.py` — `_setup_columns()` method, lines ~145–220.
