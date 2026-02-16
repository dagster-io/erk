---
title: TUI Data Contract
read_when:
  - "building an alternate frontend consuming plan data"
  - "adding fields to PlanRowData or PlanDataProvider"
  - "understanding the display-vs-raw field duality"
  - "serializing plan data to JSON for external consumers"
tripwires:
  - action: "formatting display strings during table render"
    warning: "Display strings are pre-formatted at fetch time. Add new *_display fields to PlanRowData and format in RealPlanDataProvider._build_row_data(), not in the widget layer."
  - action: "adding a field to PlanRowData without updating make_plan_row"
    warning: "The fake's make_plan_row() helper must stay in sync. Add the new field with a sensible default there too, or all TUI tests will break."
  - action: "putting PlanDataProvider ABC in src/erk/tui/"
    warning: "The ABC lives in erk-shared so provider implementations are co-located in the shared package. External consumers import from erk-shared alongside other shared gateways."
  - action: "constructing PlanFilters without copying all fields from existing filters"
    warning: "All fields must be explicitly copied in _load_data() PlanFilters construction. Missing fields (like creator) cause silent filtering failures."
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
---

# TUI Data Contract

The TUI data layer is designed around a single frozen dataclass (`PlanRowData`) that carries both display-ready strings and raw identifiers. This document explains the design decisions behind the data contract, the cross-package split, and the pitfalls of JSON serialization — things that can't be learned by reading any single source file.

## Why Display and Raw Fields Coexist

<!-- Source: src/erk/tui/data/types.py, PlanRowData -->

`PlanRowData` carries two kinds of fields for the same data. For example, `pr_number` (raw `int | None`) and `pr_display` (pre-formatted `str` like `"#123 👀"`). This is deliberate:

- **Pre-formatted display fields** (`*_display`) are computed once at fetch time, not at render time. The Textual `DataTable` renders frequently (on scroll, resize, focus changes), so pushing formatting into the data fetch keeps rendering fast and eliminates formatting inconsistencies between refreshes.
- **Raw fields** exist because TUI actions (open URL, copy to clipboard, close plan) need actual identifiers and URLs, not display strings with emoji.

This duality means every new piece of displayable data requires two fields: a raw value for actions and a display string for rendering. The formatting logic lives in `RealPlanDataProvider._build_row_data()`, not in any widget.

## The Cross-Package Split

The data types and their provider ABC live in different packages:

| Artifact                                | Location                                             | Why                               |
| --------------------------------------- | ---------------------------------------------------- | --------------------------------- |
| `PlanRowData`, `PlanFilters`            | `src/erk/tui/data/types.py`                          | TUI-specific display types        |
| `PlanDataProvider` ABC                  | `packages/erk-shared/.../plan_data_provider/abc.py`  | Shared interface for any consumer |
| `RealPlanDataProvider`                  | `packages/erk-shared/.../plan_data_provider/real.py` | Production implementation         |
| `FakePlanDataProvider`, `make_plan_row` | `packages/erk-shared/.../plan_data_provider/fake.py` | Test doubles                      |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py, PlanDataProvider -->

The ABC lives in `erk-shared` (not `src/erk/tui/`) so that the provider interface and its real/fake implementations are co-located in the shared package. Note that the ABC does import `PlanRowData` and `PlanFilters` from `erk.tui.data.types`, so it does not fully decouple from the TUI package. The primary benefit is organizational: external consumers like `erk exec dash-data` can import the provider from `erk-shared` alongside other shared gateways, keeping the dependency graph consistent.

## Data Transformation Pipeline

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, RealPlanDataProvider.fetch_plans -->

`RealPlanDataProvider.fetch_plans()` transforms data through three stages:

1. **`IssueInfo`** — Raw GitHub API response (issue number, title, body, labels)
2. **`Plan`** — Domain model with parsed metadata (state, URL, assignees, timestamps)
3. **`PlanRowData`** — Display-ready with pre-formatted strings, worktree data, and PR linkages

The key assembly step is `_build_row_data()`, which merges data from four sources in a single pass: the `Plan` domain object, PR linkages from a batched GraphQL query, local worktree filesystem scan, and plan header metadata extracted from the issue body. Understanding this merging is essential when debugging why a field shows stale data — the bug could be in any of these four sources.

## PlanRowData Field Reference

The `PlanRowData` frozen dataclass (`src/erk/tui/data/types.py`) contains 38 fields organized into 9 categories. All data is immutable to ensure table state consistency.

### Identifiers (4 fields)

| Field          | Type  | Nullable | Description                                        |
| -------------- | ----- | -------- | -------------------------------------------------- |
| `issue_number` | `int` | No       | GitHub issue number                                |
| `issue_url`    | `str` | Yes      | Full URL to the GitHub issue (None if unavailable) |
| `pr_number`    | `int` | Yes      | PR number if linked, None otherwise                |
| `pr_url`       | `str` | Yes      | URL to PR (GitHub or Graphite)                     |

### Title Fields (3 fields)

| Field        | Type  | Nullable | Description                              |
| ------------ | ----- | -------- | ---------------------------------------- |
| `title`      | `str` | No       | Plan title, may be truncated for display |
| `full_title` | `str` | No       | Complete untruncated plan title          |
| `pr_title`   | `str` | Yes      | PR title if linked                       |

### Metadata Fields (3 fields)

| Field             | Type       | Nullable | Description                                       |
| ----------------- | ---------- | -------- | ------------------------------------------------- |
| `author`          | `str`      | No       | GitHub login of the issue creator (from API)      |
| `created_at`      | `datetime` | No       | Creation datetime of the issue                    |
| `created_display` | `str`      | No       | Formatted relative time string (e.g., `"2d ago"`) |

### Body Content (1 field)

| Field        | Type  | Nullable | Description                    |
| ------------ | ----- | -------- | ------------------------------ |
| `issue_body` | `str` | No       | Raw issue body text (markdown) |

### Display Strings (10 fields)

Pre-formatted strings with emoji and relative times. Ready for direct rendering or conversion to GUI indicators.

| Field                 | Type  | Nullable | Description                          | Example                                  |
| --------------------- | ----- | -------- | ------------------------------------ | ---------------------------------------- |
| `pr_display`          | `str` | No       | Formatted PR cell content            | `"#123 👀"`, `"-"`                       |
| `checks_display`      | `str` | No       | Formatted checks cell                | `"✓"`, `"✗"`, `"-"`                      |
| `local_impl_display`  | `str` | No       | Relative time since last local impl  | `"2h ago"`, `"-"`                        |
| `remote_impl_display` | `str` | No       | Relative time since last remote impl | `"1d ago"`, `"-"`                        |
| `run_id_display`      | `str` | No       | Formatted workflow run ID            | `"123456"`, `"-"`                        |
| `run_state_display`   | `str` | No       | Formatted workflow run state         | `"✓"`, `"⟳"`, `"-"`                      |
| `comments_display`    | `str` | No       | Formatted display of comments        | `"3/5"`, `"-"`                           |
| `learn_display`       | `str` | No       | Formatted display string with text   | `"- not started"`, `"⟳ in progress"`     |
| `learn_display_icon`  | `str` | No       | Icon-only display for table          | `"-"`, `"⟳"`, `"∅"`, `"#456"`, `"✓ #12"` |
| `objective_display`   | `str` | No       | Formatted display string             | `"#123"`, `"-"`                          |

**Display String Pattern:** All `*_display` fields are pre-formatted at fetch time, not render time. This ensures table rendering is fast and consistent.

**GUI Conversion:** Desktop dashboard should replace emoji indicators with proper GUI elements (colored status dots, progress spinners, badges).

### Worktree Fields (4 fields)

| Field             | Type   | Nullable | Description                                              |
| ----------------- | ------ | -------- | -------------------------------------------------------- |
| `worktree_name`   | `str`  | No       | Name of local worktree, empty string if none             |
| `exists_locally`  | `bool` | No       | Whether worktree exists on local machine                 |
| `worktree_branch` | `str`  | Yes      | Branch name in the worktree (if exists locally)          |
| `pr_head_branch`  | `str`  | Yes      | Head branch from PR metadata (source branch for landing) |

### Timestamps (2 fields)

| Field                 | Type       | Nullable | Description                   |
| --------------------- | ---------- | -------- | ----------------------------- |
| `last_local_impl_at`  | `datetime` | Yes      | Raw timestamp for local impl  |
| `last_remote_impl_at` | `datetime` | Yes      | Raw timestamp for remote impl |

**JSON Serialization:** Datetime fields need ISO string conversion when serializing to JSON.

### GitHub Actions Fields (5 fields)

| Field            | Type                               | Nullable | Description                                                            |
| ---------------- | ---------------------------------- | -------- | ---------------------------------------------------------------------- |
| `run_id`         | `str`                              | Yes      | Raw workflow run ID (for display and URL construction)                 |
| `run_status`     | `str`                              | Yes      | Workflow run status: `"completed"`, `"in_progress"`, etc.              |
| `run_conclusion` | `str`                              | Yes      | Workflow run conclusion: `"success"`, `"failure"`, `"cancelled"`, etc. |
| `run_url`        | `str`                              | Yes      | URL to the GitHub Actions run page                                     |
| `log_entries`    | `tuple[tuple[str, str, str], ...]` | No       | List of `(event_name, timestamp, comment_url)` tuples for plan log     |

### PR State Fields (3 fields)

| Field                    | Type  | Nullable | Description                                |
| ------------------------ | ----- | -------- | ------------------------------------------ |
| `pr_state`               | `str` | Yes      | PR state: `"OPEN"`, `"MERGED"`, `"CLOSED"` |
| `resolved_comment_count` | `int` | No       | Count of resolved PR review comments       |
| `total_comment_count`    | `int` | No       | Total count of PR review comments          |

### Learn Status Fields (5 fields)

| Field                     | Type   | Nullable | Description                                               |
| ------------------------- | ------ | -------- | --------------------------------------------------------- |
| `learn_status`            | `str`  | Yes      | Raw learn status value from plan header                   |
| `learn_plan_issue`        | `int`  | Yes      | Plan issue number (for `completed_with_plan` status)      |
| `learn_plan_issue_closed` | `bool` | Yes      | Whether the learn plan issue is closed                    |
| `learn_plan_pr`           | `int`  | Yes      | PR number (for `plan_completed` status)                   |
| `learn_run_url`           | `str`  | Yes      | URL to GitHub Actions workflow run (for `pending` status) |

### Objective Fields (1 field)

| Field             | Type  | Nullable | Description                                              |
| ----------------- | ----- | -------- | -------------------------------------------------------- |
| `objective_issue` | `int` | Yes      | Objective issue number (for linking plans to objectives) |

## PlanDataProvider ABC

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py, PlanDataProvider -->

Abstract interface for fetching plan data. Implementations must provide 3 abstract properties and 5 abstract methods:

**Properties:** `repo_root` (Path), `clipboard` (Clipboard), `browser` (BrowserLauncher)

**Methods:**

| Method                  | Signature                              | Returns                     |
| ----------------------- | -------------------------------------- | --------------------------- |
| `fetch_plans`           | `(filters: PlanFilters)`               | `list[PlanRowData]`         |
| `close_plan`            | `(issue_number: int, issue_url: str)`  | `list[int]` (PR numbers)    |
| `submit_to_queue`       | `(issue_number: int, issue_url: str)`  | `None`                      |
| `fetch_branch_activity` | `(rows: list[PlanRowData])`            | `dict[int, BranchActivity]` |
| `fetch_plan_content`    | `(issue_number: int, issue_body: str)` | `str \| None`               |

## PlanFilters

<!-- Source: src/erk/tui/data/types.py, PlanFilters -->

Filter options for plan list queries. Frozen dataclass with 7 fields:

| Field       | Type              | Description                                |
| ----------- | ----------------- | ------------------------------------------ |
| `labels`    | `tuple[str, ...]` | Filter by labels (default: `["erk-plan"]`) |
| `state`     | `str \| None`     | `"open"`, `"closed"`, or None for all      |
| `run_state` | `str \| None`     | Filter by workflow run state               |
| `limit`     | `int \| None`     | Maximum number of results                  |
| `show_prs`  | `bool`            | Whether to include PR data                 |
| `show_runs` | `bool`            | Whether to include workflow run data       |
| `creator`   | `str \| None`     | Filter by creator username                 |

Also provides `PlanFilters.default()` factory for standard open erk-plan queries.

## JSON Serialization Gotchas

<!-- Source: src/erk/cli/commands/exec/scripts/dash_data.py, _serialize_plan_row -->

The `erk exec dash-data` command serializes `PlanRowData` to JSON for the desktop dashboard. `dataclasses.asdict()` handles most fields, but three types need manual conversion:

| Type                                | Problem                                                                                              | Fix                                                    |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `datetime` fields                   | `asdict()` preserves `datetime` objects, which aren't JSON-serializable                              | Convert to ISO 8601 strings via `.isoformat()`         |
| `tuple[tuple[...]]` (`log_entries`) | JSON has no tuple type; `asdict()` converts to nested lists but nested tuples need explicit handling | Convert to list of lists                               |
| Display strings with emoji          | Emoji in `*_display` fields may cause encoding or rendering issues in some frontends                 | Frontend-specific; the contract doesn't normalize them |

The production serialization lives in `_serialize_plan_row()` in `dash_data.py`. Any new `PlanRowData` field with a non-primitive type will need a corresponding serialization handler there.

## Adding a New Field: Checklist

Adding a field to `PlanRowData` touches at minimum five places. Missing any one causes test failures or silent data loss:

1. **`PlanRowData`** in `src/erk/tui/data/types.py` — add the field definition
2. **`RealPlanDataProvider._build_row_data()`** — populate it from source data
3. **`make_plan_row()`** in the fake module — add a parameter with sensible default
4. **`_serialize_plan_row()`** in `dash_data.py` — handle if non-primitive type
5. **Widget layer** — consume the field for display or action (if applicable)

If the field is a display field, also add the raw counterpart (or vice versa) following the duality pattern.

## Related Documentation

- [TUI Architecture Overview](architecture.md) — Overall TUI structure and layer boundaries
- [TUI Action Command Inventory](action-inventory.md) — Commands that consume PlanRowData fields
- [Erk Desktop Dashboard](../desktop-dash/) — Alternate frontend consuming this data contract
