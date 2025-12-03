# Plan: Add Plan Detail Modal to erk dash

## Summary

Add a modal that opens when pressing spacebar on a selected plan in `erk dash`. The modal displays:
- Full plan title (not truncated)
- PR title (if linked)
- Detailed local and remote run information

## Implementation

### 1. Extend `PlanRowData` to store additional data

**File**: `src/erk/tui/data/types.py`

Add new fields to `PlanRowData`:
- `full_title: str` - The complete, untruncated plan title
- `pr_title: str | None` - PR title if linked
- `pr_state: str | None` - PR state (e.g., "OPEN", "MERGED", "CLOSED")
- `worktree_branch: str | None` - Branch name in the worktree (if exists locally)
- `last_local_impl_at: datetime | None` - Raw timestamp for local impl
- `last_remote_impl_at: datetime | None` - Raw timestamp for remote impl
- `run_id: str | None` - Raw workflow run ID (for display and URL construction)
- `run_status: str | None` - Workflow run status (e.g., "completed", "in_progress")
- `run_conclusion: str | None` - Workflow run conclusion (e.g., "success", "failure", "cancelled")
- `log_entries: list[tuple[str, str, str]]` - List of (event_name, timestamp, comment_url) for plan log

Note: Worktree path is derived in the modal from worktree_name + known worktree location, not stored.

### 1b. Add `IssueComment` dataclass and extend issues ABC

**File**: `packages/erk-shared/src/erk_shared/github/issues/abc.py`

Add new dataclass:
```python
@dataclass(frozen=True)
class IssueComment:
    body: str
    url: str  # html_url of the comment
```

Add new method to `GitHubIssues` ABC:
```python
@abstractmethod
def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
    """Fetch all comments with their URLs for an issue."""
    ...
```

**File**: `packages/erk-shared/src/erk_shared/github/issues/real.py`

Implement using jq to extract both body and html_url:
```python
"[.[] | {body, url: .html_url}]"
```

**File**: `packages/erk-shared/src/erk_shared/github/issues/fake.py`

Update fake to store and return comment URLs.

### 2. Update `RealPlanDataProvider._build_row_data()` to populate new fields

**File**: `src/erk/tui/data/provider.py`

In `_build_row_data()`:
- Store `plan.title` as `full_title` (before truncation)
- Extract `selected_pr.title` if PR is linked
- Pass through `last_local_impl_at` and `last_remote_impl_at` as raw datetime objects
- Extract `workflow_run.status` and `workflow_run.conclusion` if available

Also update `_build_worktree_mapping()`:
- Change return type from `dict[int, str]` to `dict[int, tuple[str, str | None]]` (name, branch)
- Store `(worktree.path.name, worktree.branch)` instead of just the name
- Update `_build_row_data()` to extract branch from the mapping

### 3. Create `PlanDetailScreen` modal

**File**: `src/erk/tui/app.py` (add new class alongside HelpScreen)

Create new modal following the `HelpScreen` pattern:
- Extend `ModalScreen`
- Accept `PlanRowData` and clipboard interface in constructor
- Define CSS for dialog styling (similar to HelpScreen)
- Bindings: escape, q, space to dismiss
- Compose sections:
  - Header: "Plan #123" as clickable link + [copy url] button
  - Title + Status
  - PR section (if linked): #456 link, title, state, checkout [copy]
  - Local section: worktree name, branch, exists status, last run time
  - Remote section: run ID + [copy url], last run time, status/conclusion
  - Footer: "Press Esc or Space to close"

Interactive elements implementation:
- Use Textual `Button` widgets for [copy] and [copy url] actions
- Use Rich markup `[@click=...]` or custom widgets for clickable links
- Copy actions use clipboard interface passed from ErkDashApp
- Links use `click.launch()` to open URLs in browser

### 4. Add spacebar binding to `ErkDashApp`

**File**: `src/erk/tui/app.py`

Add to `BINDINGS`:
```python
Binding("space", "show_detail", "Detail"),
```

Add action method:
```python
def action_show_detail(self) -> None:
    """Show plan detail modal for selected row."""
    row = self._get_selected_row()
    if row is None:
        return
    self.push_screen(PlanDetailScreen(row))
```

### 5. Update HelpScreen to document spacebar

**File**: `src/erk/tui/app.py`

Add to the Actions section in HelpScreen.compose():
```python
yield Label("Space   View plan details", classes="help-binding")
```

### 6. Add tests

**File**: `tests/tui/test_app.py`

Add tests for:
- Spacebar opens PlanDetailScreen with correct data
- Modal displays full title correctly
- Modal dismisses on escape/q/space
- Modal shows PR title when linked
- Modal shows "-" when no PR linked

## Modal Layout

```
┌─────────────────────────────────────────────────────┐
│                Plan #123 (link)         [copy url]  │
├─────────────────────────────────────────────────────┤
│ Title: Add spacebar modal to show full plan         │
│        details with all the information             │
│ Status: open                                        │
│                                                     │
│ PR                                                  │
│   #456 (link)                           [copy url]  │
│   Title: Implement plan detail modal                │
│   Status: open ✓                                    │
│   Checkout: erk pr co 456                    [copy] │
│                                                     │
│ Local                                               │
│   Worktree: plan-123-feature                        │
│   Branch: plan-123-feature                          │
│   Status: exists ✓                                  │
│   Last run: 2h ago                                  │
│                                                     │
│ Remote                                              │
│   Run: 9812983123                       [copy url]  │
│   Last run: 1h ago                                  │
│   Status: completed (success)                       │
│                                                     │
│ Log                                                 │
│   • 2h ago  plan_created (link)                     │
│   • 1h ago  worktree_created (link)                 │
│   • 45m ago submission_queued (link)                │
│   • 30m ago workflow_started (link)                 │
│                                                     │
│            Press Esc or Space to close              │
└─────────────────────────────────────────────────────┘
```

Interactive elements:
- Plan #123: clickable link to issue + [copy url] button
- PR #456: clickable link to PR + [copy url] button
- Checkout command: [copy] button copies "erk pr co 456"
- Run ID: displayed as number + [copy url] button for GitHub Actions URL
- Log entries: each event name is a clickable link to the GitHub comment

## Files to Modify

1. `packages/erk-shared/src/erk_shared/github/issues/abc.py` - Add IssueComment dataclass and new ABC method
2. `packages/erk-shared/src/erk_shared/github/issues/real.py` - Implement get_issue_comments_with_urls
3. `packages/erk-shared/src/erk_shared/github/issues/fake.py` - Update fake to return comment URLs
4. `packages/erk-shared/src/erk_shared/github/issues/dry_run.py` - Delegate new method
5. `src/erk/tui/data/types.py` - Add fields to PlanRowData
6. `src/erk/tui/data/provider.py` - Populate new fields, fetch log entries
7. `src/erk/tui/app.py` - Add PlanDetailScreen and spacebar binding
8. `tests/tui/test_app.py` - Add tests for new functionality
9. `tests/tui/fakes.py` - Update FakePlanDataProvider if needed