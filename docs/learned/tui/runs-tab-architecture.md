---
title: "Runs Tab Architecture"
read_when:
  - "working with TUI Runs tab"
  - "adding columns to RunDataTable"
  - "understanding branch resolution in runs"
  - "modifying workflow run display in TUI"
tripwires:
  - action: "using run.branch directly for display without checking PR head_branch first"
    warning: "After merge+deletion, run.branch becomes master/main. Use PR head_branch as primary source, falling back to run.branch only if not master/main."
  - action: "adding a new column to RunDataTable without updating RunRowData"
    warning: "RunDataTable columns are populated from RunRowData fields. Add the field to RunRowData first, then add the column in _setup_columns."
---

# Runs Tab Architecture

The Runs tab displays GitHub Actions workflow runs in the TUI, alongside Plans, Learn, and Objectives views.

## RunRowData

Frozen dataclass representing one workflow run row.

**Source**: `src/erk/tui/data/types.py`

| Field               | Type               | Description                                                                  |
| ------------------- | ------------------ | ---------------------------------------------------------------------------- |
| `run_id`            | `str`              | GitHub Actions workflow run ID                                               |
| `run_url`           | `str \| None`      | URL to the GitHub Actions run page                                           |
| `status`            | `str`              | Raw status: "queued", "in_progress", "completed"                             |
| `conclusion`        | `str \| None`      | Raw conclusion: "success", "failure", "cancelled", None                      |
| `workflow_name`     | `str`              | Workflow command name (e.g., "plan-implement")                               |
| `pr_number`         | `int \| None`      | Associated PR number                                                         |
| `pr_url`            | `str \| None`      | PR URL (Graphite URL if configured)                                          |
| `pr_display`        | `str`              | Formatted PR display string                                                  |
| `pr_state`          | `str \| None`      | PR state ("OPEN", "MERGED", "CLOSED"). None if no PR.                        |
| `pr_title`          | `str \| None`      | PR title. None if no PR.                                                     |
| `pr_status_display` | `str`              | Pre-formatted PR status emoji (e.g., "👀", "🚧", "🎉", "⛔", or "-")        |
| `branch`            | `str`              | Source branch from workflow run                                              |
| `branch_display`    | `str`              | Truncated branch name (max 40 chars)                                         |
| `submitted_display` | `str`              | Formatted time (e.g., "03-09 14:30")                                         |
| `status_display`    | `str`              | Formatted status with conclusion                                             |
| `checks_display`    | `str`              | CI checks summary                                                            |
| `created_at`        | `datetime \| None` | UTC creation time                                                            |
| `run_id_display`    | `str`              | Formatted run ID for display                                                 |
| `title_display`     | `str`              | Truncated title for table display                                            |

## RunDataTable Widget

**Source**: `src/erk/tui/widgets/run_table.py`

Column configuration in `_setup_columns`:

| Column    | Key       | Width |
| --------- | --------- | ----- |
| run-id    | run_id    | 12    |
| status    | status    | 14    |
| submitted | submitted | 12    |
| workflow  | workflow  | 16    |
| pr        | pr        | 8     |
| pr-st     | pr_st     | 6     |
| branch    | branch    | 40    |
| chks      | chks      | 8     |

The `pr-st` column (key `pr_st`) shows `RunRowData.pr_status_display` — a PR state emoji indicating the PR's current status (open/draft/merged/closed). It appears between the `pr` and `branch` columns.

Features:

- Row-selection mode (`cursor_type="row"`)
- Messages: `RunClicked` (run-id click), `PrClicked` (pr click)
- Cursor position preservation on refresh via `selected_key`
- Left/right arrow keys delegate to app's `action_previous_view()` / `action_next_view()`
- Cell values rendered with Textual markup links: `[link={url}]text[/link]`

## Branch Resolution

**Source**: `src/erk/tui/data/real_provider.py` (fetch_runs)

Branch display uses a priority chain because after merge+deletion, `run.branch` becomes the default branch:

1. **PR head_branch** (from `get_pr_head_branches()`) — original feature branch name
2. **run.branch** (if not "master" or "main") — direct branch reference
3. **"-"** — when no branch is available

## get_pr_head_branches Gateway Method

**Source**: `packages/erk-shared/src/erk_shared/gateway/github/abc.py`

See source file for the current method signature.

Batch-fetches head branch names for PR numbers in a single GraphQL query. Follows the 4-place gateway pattern (ABC, Real, Fake, DryRun). Missing PRs are omitted from the returned dict.

## Data Flow

1. Fetch workflow runs from all registered workflows (`WORKFLOW_COMMAND_MAP`)
2. Extract PR numbers from `display_title` and plan numbers
3. Build plan-to-run-ids lookup for batch PR linkage
4. Batch fetch PR linkages for plan-number runs
5. Fetch PR info for directly-extracted PR numbers
6. Build `RunRowData` for each run

## j/k Navigation

**Source**: `src/erk/tui/actions/navigation.py`

The j/k key dispatch routes to the appropriate table based on `_view_mode`:

- `ViewMode.RUNS` → delegates to `_run_table.action_cursor_down/up()`
- Other modes → delegates to `_table.action_cursor_down/up()`

View switching to Runs tab uses the "4" key.
