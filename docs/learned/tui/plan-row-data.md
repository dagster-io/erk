---
title: PlanRowData Field Reference
read_when:
  - "writing command availability predicates"
  - "understanding what data is available for TUI commands"
  - "checking which PlanRowData fields are nullable"
---

# PlanRowData Field Reference

Quick reference of `PlanRowData` fields for writing command availability predicates.

## Overview

`PlanRowData` is a frozen dataclass containing all data for a single plan row in the TUI. It combines raw data (for actions) with pre-formatted display strings (for table rendering).

**Location:** `src/erk/tui/data/types.py`

## Field Categories

### Issue Info

| Field          | Type          | Description                   | Nullable?                     |
| -------------- | ------------- | ----------------------------- | ----------------------------- |
| `issue_number` | `int`         | GitHub issue number           | Never                         |
| `issue_url`    | `str \| None` | Full URL to GitHub issue      | Yes                           |
| `title`        | `str`         | Plan title (may be truncated) | Never (empty string possible) |
| `full_title`   | `str`         | Complete untruncated title    | Never (empty string possible) |

### PR Info

| Field                    | Type          | Description                            | Nullable?                   |
| ------------------------ | ------------- | -------------------------------------- | --------------------------- |
| `pr_number`              | `int \| None` | PR number if linked                    | Yes                         |
| `pr_url`                 | `str \| None` | URL to PR (GitHub or Graphite)         | Yes                         |
| `pr_display`             | `str`         | Formatted PR cell (e.g., "#123 👀")    | Never (empty/dash possible) |
| `pr_title`               | `str \| None` | PR title if different from issue       | Yes                         |
| `pr_state`               | `str \| None` | PR state: "OPEN", "MERGED", "CLOSED"   | Yes                         |
| `checks_display`         | `str`         | Formatted checks cell (e.g., "✓", "✗") | Never (dash possible)       |
| `resolved_comment_count` | `int`         | Count of resolved PR review comments   | Never (0 if no PR)          |
| `total_comment_count`    | `int`         | Total count of PR review comments      | Never (0 if no PR)          |
| `comments_display`       | `str`         | Formatted comments (e.g., "3/5", "-")  | Never (dash if no PR)       |

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

### Objective Info

| Field              | Type          | Description                          | Nullable?             |
| ------------------ | ------------- | ------------------------------------ | --------------------- |
| `objective_issue`  | `int \| None` | Linked objective issue number        | Yes                   |
| `objective_display` | `str`         | Formatted objective (e.g., "#42")    | Never (dash possible) |

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

## Common Availability Patterns

### Check if PR exists

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

### Check if issue URL exists

```python
is_available=lambda ctx: ctx.row.issue_url is not None
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

# Either PR or issue URL exists
is_available=lambda ctx: bool(ctx.row.pr_url or ctx.row.issue_url)
```

### Always available

```python
is_available=lambda _: True
```

## Display vs Raw Fields

Many pieces of data have both a raw value and a display value:

| Raw Field                                      | Display Field              | Purpose                 |
| ---------------------------------------------- | -------------------------- | ----------------------- |
| `issue_number`                                 | (used directly in display) | Issue number            |
| `pr_number`                                    | `pr_display`               | PR with state indicator |
| `resolved_comment_count`/`total_comment_count` | `comments_display`         | Comment counts (X/Y)    |
| `objective_issue`                              | `objective_display`        | Objective reference     |
| `run_id`                                       | `run_id_display`           | Run ID formatted        |
| `run_status`/`run_conclusion`                  | `run_state_display`        | Human-readable state    |
| `title`                                        | (is already display)       | Truncated title         |
| `full_title`                                   | (is raw)                   | Full title for modals   |

**Rule:** Use raw fields in predicates (for `None` checks), display fields for rendering.

## Testing with make_plan_row()

The test helper `make_plan_row()` in `tests/fakes/plan_data_provider.py` creates `PlanRowData` instances with sensible defaults. Override only the fields you need:

```python
from tests.fakes.plan_data_provider import make_plan_row

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

# With objective issue
row = make_plan_row(123, "Test", objective_issue=42)
```

## Related Topics

- [adding-commands.md](adding-commands.md) - How to add new TUI commands
- [architecture.md](architecture.md) - Overall TUI architecture
