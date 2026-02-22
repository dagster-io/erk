---
title: PlanRowData Field Reference
read_when:
  - "writing command availability predicates"
  - "understanding what data is available for TUI commands"
  - "checking which PlanRowData fields are nullable"
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# PlanRowData Field Reference

Quick reference of `PlanRowData` fields for writing command availability predicates.

## Overview

`PlanRowData` is a frozen dataclass containing all data for a single plan row in the TUI. It combines raw data (for actions) with pre-formatted display strings (for table rendering).

**Location:** `src/erk/tui/data/types.py`

## Field Categories

### Plan Info

| Field        | Type          | Description                   | Nullable?                     |
| ------------ | ------------- | ----------------------------- | ----------------------------- |
| `plan_id`    | `int`         | Plan identifier               | Never                         |
| `plan_url`   | `str \| None` | Full URL to the plan          | Yes                           |
| `full_title` | `str`         | Complete plan title           | Never (empty string possible) |
| `plan_body`  | `str`         | Raw plan body text (markdown) | Never (empty string possible) |

### PR Info

| Field                    | Type           | Description                                | Nullable?                   |
| ------------------------ | -------------- | ------------------------------------------ | --------------------------- |
| `pr_number`              | `int \| None`  | PR number if linked                        | Yes                         |
| `pr_url`                 | `str \| None`  | URL to PR (GitHub or Graphite)             | Yes                         |
| `pr_display`             | `str`          | Formatted PR cell (e.g., "#123 👀")        | Never (empty/dash possible) |
| `pr_title`               | `str \| None`  | PR title if different from issue           | Yes                         |
| `pr_state`               | `str \| None`  | PR state: "OPEN", "MERGED", "CLOSED"       | Yes                         |
| `pr_head_branch`         | `str \| None`  | Head branch from PR metadata (for landing) | Yes                         |
| `checks_display`         | `str`          | Formatted checks cell (e.g., "✓", "✗")     | Never (dash possible)       |
| `resolved_comment_count` | `int`          | Count of resolved PR review comments       | Never (0 if no PR)          |
| `total_comment_count`    | `int`          | Total count of PR review comments          | Never (0 if no PR)          |
| `pr_has_conflicts`       | `bool \| None` | Whether the PR has merge conflicts         | Yes (None if unknown/no PR) |
| `comments_display`       | `str`          | Formatted comments (e.g., "3/5", "-")      | Never (dash if no PR)       |

### Lifecycle & Status

| Field               | Type  | Description                                            | Nullable?             |
| ------------------- | ----- | ------------------------------------------------------ | --------------------- |
| `lifecycle_display` | `str` | Formatted lifecycle stage (e.g., "[cyan]impld[/cyan]") | Never (dash possible) |
| `pr_status_display` | `str` | PR status emoji indicators (e.g., "👀💥", "-")         | Never (dash possible) |

### Worktree Info

| Field             | Type          | Description                             | Nullable?                    |
| ----------------- | ------------- | --------------------------------------- | ---------------------------- |
| `worktree_name`   | `str`         | Name of local worktree                  | Never (empty string if none) |
| `worktree_branch` | `str \| None` | Branch name in worktree                 | Yes                          |
| `exists_locally`  | `bool`        | Whether worktree exists on this machine | Never                        |

### Implementation Info

| Field                 | Type               | Description                          | Nullable?             |
| --------------------- | ------------------ | ------------------------------------ | --------------------- |
| `local_impl_display`  | `str`              | Relative time since last local impl  | Never (dash possible) |
| `remote_impl_display` | `str`              | Relative time since last remote impl | Never (dash possible) |
| `last_local_impl_at`  | `datetime \| None` | Raw timestamp for local impl         | Yes                   |
| `last_remote_impl_at` | `datetime \| None` | Raw timestamp for remote impl        | Yes                   |

### Run Info (GitHub Actions)

| Field               | Type          | Description                                       | Nullable?             |
| ------------------- | ------------- | ------------------------------------------------- | --------------------- |
| `run_id`            | `str \| None` | Raw workflow run ID                               | Yes                   |
| `run_id_display`    | `str`         | Formatted run ID for display                      | Never (dash possible) |
| `run_url`           | `str \| None` | URL to GitHub Actions run page                    | Yes                   |
| `run_status`        | `str \| None` | Run status: "completed", "in_progress", "queued"  | Yes                   |
| `run_conclusion`    | `str \| None` | Run conclusion: "success", "failure", "cancelled" | Yes                   |
| `run_state_display` | `str`         | Formatted run state                               | Never (dash possible) |

### Activity Log

| Field         | Type                               | Description                                  | Nullable?                    |
| ------------- | ---------------------------------- | -------------------------------------------- | ---------------------------- |
| `log_entries` | `tuple[tuple[str, str, str], ...]` | List of (event_name, timestamp, comment_url) | Never (empty tuple possible) |

### Learn Info

| Field                     | Type           | Description                                         | Nullable?             |
| ------------------------- | -------------- | --------------------------------------------------- | --------------------- |
| `learn_status`            | `str \| None`  | Raw learn status value from plan header             | Yes                   |
| `learn_plan_issue`        | `int \| None`  | Plan issue number (for completed_with_plan status)  | Yes                   |
| `learn_plan_issue_closed` | `bool \| None` | Whether the learn plan issue is closed              | Yes                   |
| `learn_plan_pr`           | `int \| None`  | PR number (for plan_completed status)               | Yes                   |
| `learn_run_url`           | `str \| None`  | URL to GitHub Actions workflow run (pending status) | Yes                   |
| `learn_display`           | `str`          | Formatted display string (e.g., "- not started")    | Never (dash possible) |
| `learn_display_icon`      | `str`          | Icon-only display for table (e.g., "-", "⟳", "∅")   | Never (dash possible) |

### Objective Info

| Field                         | Type          | Description                                           | Nullable?             |
| ----------------------------- | ------------- | ----------------------------------------------------- | --------------------- |
| `objective_issue`             | `int \| None` | Objective issue number (linking plans to objectives)  | Yes                   |
| `objective_display`           | `str`         | Formatted display string (e.g., "#123" or "-")        | Never (dash possible) |
| `objective_done_nodes`        | `int`         | Count of done nodes in objective roadmap              | Never (0 if no obj)   |
| `objective_total_nodes`       | `int`         | Total nodes in objective roadmap                      | Never (0 if no obj)   |
| `objective_progress_display`  | `str`         | Progress display (e.g., "3/7" or "-")                 | Never (dash possible) |
| `objective_next_node_display` | `str`         | Next pending node (e.g., "1.3 Add tests" or "-")      | Never (dash possible) |
| `objective_deps_display`      | `str`         | Dep status of next node ("ready", "in progress", "-") | Never (dash possible) |

### Metadata

| Field             | Type       | Description                                           | Nullable? |
| ----------------- | ---------- | ----------------------------------------------------- | --------- |
| `updated_at`      | `datetime` | Last update datetime of the issue                     | Never     |
| `updated_display` | `str`      | Formatted relative time (e.g., "2h ago")              | Never     |
| `created_at`      | `datetime` | Creation datetime of the issue                        | Never     |
| `created_display` | `str`      | Formatted relative time (e.g., "2d ago")              | Never     |
| `author`          | `str`      | GitHub login of the issue creator                     | Never     |
| `is_learn_plan`   | `bool`     | Whether this is a learn plan (has [erk-learn] prefix) | Never     |

## Common Availability Patterns

### Check if PR exists

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

### Check if plan URL exists

```python
is_available=lambda ctx: ctx.row.plan_url is not None
```

### Check if worktree exists locally

```python
is_available=lambda ctx: ctx.row.exists_locally
```

### Check if workflow run exists

```python
is_available=lambda ctx: ctx.row.run_url is not None
```

### Compound conditions

```python
# PR exists AND worktree exists locally
is_available=lambda ctx: ctx.row.pr_number is not None and ctx.row.exists_locally

# Either PR or plan URL exists
is_available=lambda ctx: bool(ctx.row.pr_url or ctx.row.plan_url)
```

### Always available

```python
is_available=lambda _: True
```

## Display vs Raw Fields

Many pieces of data have both a raw value and a display value:

| Raw Field                                      | Display Field                        | Purpose                 |
| ---------------------------------------------- | ------------------------------------ | ----------------------- |
| `plan_id`                                      | (used directly in display)           | Plan identifier         |
| `pr_number`                                    | `pr_display`                         | PR with state indicator |
| `resolved_comment_count`/`total_comment_count` | `comments_display`                   | Comment counts (X/Y)    |
| `run_id`                                       | `run_id_display`                     | Run ID formatted        |
| `run_status`/`run_conclusion`                  | `run_state_display`                  | Human-readable state    |
| `full_title`                                   | (used directly in display)           | Full plan title         |
| `learn_status`                                 | `learn_display`/`learn_display_icon` | Learn workflow state    |
| `objective_issue`                              | `objective_display`                  | Objective link          |
| `objective_done_nodes`/`objective_total_nodes` | `objective_progress_display`         | Objective progress      |
| (none)                                         | `objective_next_node_display`        | Next objective node     |
| (none)                                         | `objective_deps_display`             | Next node dep status    |
| `updated_at`                                   | `updated_display`                    | Last update time        |
| `created_at`                                   | `created_display`                    | Creation time           |
| `author`                                       | (used directly in display)           | Issue creator           |
| `is_learn_plan`                                | (boolean flag)                       | Learn plan indicator    |

**Rule:** Use raw fields in predicates (for `None` checks), display fields for rendering.

## Testing with make_plan_row()

The test helper `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` creates `PlanRowData` instances with sensible defaults. Override only the fields you need:

```python
from erk_shared.gateway.plan_data_provider.fake import make_plan_row

# Minimal row
row = make_plan_row(123, "Test Plan")

# With PR
row = make_plan_row(123, "Test", pr_number=456, pr_url="https://...")

# With PR and comment counts (resolved, total)
row = make_plan_row(123, "Test", pr_number=456, comment_counts=(3, 5))

# With local worktree
row = make_plan_row(123, "Test", worktree_name="feature-123", exists_locally=True)

# With workflow run
row = make_plan_row(123, "Test", run_url="https://github.com/.../runs/789")
```

## Related Topics

- [adding-commands.md](adding-commands.md) - How to add new TUI commands
- [architecture.md](architecture.md) - Overall TUI architecture
