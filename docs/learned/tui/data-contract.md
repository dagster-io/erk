---
title: TUI Data Contract Reference
read_when:
  - "building on top of the TUI data layer"
  - "serializing PlanRowData to JSON"
  - "understanding what data the dashboard displays"
---

# TUI Data Contract Reference

Complete reference for the TUI data layer: PlanRowData fields, PlanDataProvider interface, and data fetch patterns. Essential for building alternate frontends (desktop dashboard, web interface) that consume the same data.

## PlanRowData Fields

The `PlanRowData` frozen dataclass contains 40 fields organized into 7 categories. All data is immutable to ensure table state consistency.

### Identifiers (4 fields)

| Field          | Type  | Nullable | Description                         |
| -------------- | ----- | -------- | ----------------------------------- |
| `issue_number` | `int` | No       | GitHub issue number                 |
| `issue_url`    | `str` | Yes      | Full URL to the GitHub issue        |
| `pr_number`    | `int` | Yes      | PR number if linked, None otherwise |
| `pr_url`       | `str` | Yes      | URL to PR (GitHub or Graphite)      |

### Title Fields (3 fields)

| Field        | Type  | Nullable | Description                              |
| ------------ | ----- | -------- | ---------------------------------------- |
| `title`      | `str` | No       | Plan title, may be truncated for display |
| `full_title` | `str` | No       | Complete untruncated plan title          |
| `pr_title`   | `str` | Yes      | PR title if linked                       |

### Body Content (1 field)

| Field        | Type  | Nullable | Description                    |
| ------------ | ----- | -------- | ------------------------------ |
| `issue_body` | `str` | No       | Raw issue body text (markdown) |

### Display Strings (8 fields)

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

### PR State Fields (4 fields)

| Field                    | Type  | Nullable | Description                                |
| ------------------------ | ----- | -------- | ------------------------------------------ |
| `pr_state`               | `str` | Yes      | PR state: `"OPEN"`, `"MERGED"`, `"CLOSED"` |
| `resolved_comment_count` | `int` | No       | Count of resolved PR review comments       |
| `total_comment_count`    | `int` | No       | Total count of PR review comments          |
| `comments_display`       | `str` | No       | Formatted display (e.g., `"3/5"` or `"-"`) |

### Learn Status Fields (5 fields)

| Field                     | Type   | Nullable | Description                                               |
| ------------------------- | ------ | -------- | --------------------------------------------------------- |
| `learn_status`            | `str`  | Yes      | Raw learn status value from plan header                   |
| `learn_plan_issue`        | `int`  | Yes      | Plan issue number (for `completed_with_plan` status)      |
| `learn_plan_issue_closed` | `bool` | Yes      | Whether the learn plan issue is closed                    |
| `learn_plan_pr`           | `int`  | Yes      | PR number (for `plan_completed` status)                   |
| `learn_run_url`           | `str`  | Yes      | URL to GitHub Actions workflow run (for `pending` status) |

### Objective Fields (2 fields)

| Field               | Type  | Nullable | Description                                              |
| ------------------- | ----- | -------- | -------------------------------------------------------- |
| `objective_issue`   | `int` | Yes      | Objective issue number (for linking plans to objectives) |
| `objective_display` | `str` | No       | Formatted display string (e.g., `"#123"` or `"-"`)       |

## PlanDataProvider ABC

Abstract interface for fetching plan data. Implementations must provide this interface.

```python
class PlanDataProvider(ABC):
    @property
    @abstractmethod
    def repo_root(self) -> Path:
        """Get the repository root path."""
        ...

    @property
    @abstractmethod
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        ...

    @property
    @abstractmethod
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs."""
        ...

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Fetch plans matching the given filters."""
        ...

    @abstractmethod
    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close a plan and its linked PRs. Returns list of PR numbers closed."""
        ...

    @abstractmethod
    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit a plan to the implementation queue."""
        ...

    @abstractmethod
    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally."""
        ...

    @abstractmethod
    def fetch_plan_content(self, issue_number: int, issue_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue."""
        ...
```

## PlanFilters

Filter options for plan list queries.

```python
@dataclass(frozen=True)
class PlanFilters:
    labels: tuple[str, ...]      # Filter by labels (default: ["erk-plan"])
    state: str | None            # "open", "closed", or None for all
    run_state: str | None        # Filter by workflow run state
    limit: int | None            # Maximum number of results
    show_prs: bool               # Whether to include PR data
    show_runs: bool              # Whether to include workflow run data
    creator: str | None          # Filter by creator username
```

## RealPlanDataProvider Data Fetch Flow

The production implementation follows this sequence:

1. **Fetch from GitHub API** via `PlanListService`
2. **Build worktree mapping** from local filesystem (scan `.git/worktrees/`)
3. **Transform data** through three layers:
   - `IssueInfo` (raw GitHub API response)
   - `Plan` (domain model with linked PR/worktree)
   - `PlanRowData` (display-ready with pre-formatted strings)
4. **Apply filters** before returning (labels, state, run_state, limit)

**Key Pattern:** Pre-format all display strings during fetch, not during render. This makes table rendering fast and ensures consistency.

## JSON Serialization Considerations

When serializing PlanRowData to JSON (for desktop dashboard CLI command):

1. **Datetime fields** need ISO string conversion:
   - `last_local_impl_at` → `isoformat()`
   - `last_remote_impl_at` → `isoformat()`

2. **Tuple fields** need list conversion:
   - `log_entries` → convert nested tuples to nested lists

3. **Display strings** contain emoji that may need special handling depending on the consuming frontend

Example serialization:

```python
def serialize_plan_row_data(row: PlanRowData) -> dict:
    return {
        **asdict(row),
        "last_local_impl_at": row.last_local_impl_at.isoformat() if row.last_local_impl_at else None,
        "last_remote_impl_at": row.last_remote_impl_at.isoformat() if row.last_remote_impl_at else None,
        "log_entries": [list(entry) for entry in row.log_entries],
    }
```

## Related Documentation

- [TUI Architecture Overview](architecture.md) - Overall TUI structure
- [TUI Action Command Inventory](action-inventory.md) - Commands that consume this data
- [Erk Desktop Dashboard](../desktop-dash/) - Alternate frontend consuming this data contract
