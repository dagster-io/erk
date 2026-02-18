# Unresolved Comments Modal for erk dash

## Context

The erk dash TUI shows plans with a "comments" column displaying resolved/total counts (e.g., "1/4"). The user wants to press `c` on a selected row to see the actual unresolved PR review threads in a modal, so they can quickly assess whether to dispatch an "address" job.

Key insight: all the data-fetching infrastructure already exists. `RealGitHub.get_pr_review_threads()` fetches and parses review threads via GraphQL, and `IssueBodyScreen` provides the exact modal pattern to replicate.

## Step 1: Add `fetch_unresolved_comments` to PlanDataProvider ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`

Add abstract method after `fetch_objective_content`:

```python
@abstractmethod
def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
    """Fetch unresolved review threads for a pull request.

    Args:
        pr_number: The PR number to fetch threads for

    Returns:
        List of unresolved PRReviewThread objects sorted by (path, line)
    """
    ...
```

Add import: `from erk_shared.gateway.github.types import PRReviewThread`

## Step 2: Implement in RealPlanDataProvider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

Add after `fetch_objective_content` (around line 404):

```python
def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
    return self._ctx.github.get_pr_review_threads(
        self._location.root, pr_number, include_resolved=False
    )
```

Add import: `from erk_shared.gateway.github.types import PRReviewThread` (likely already partially imported from this module)

## Step 3: Implement in FakePlanDataProvider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

- Add `self._review_threads_by_pr: dict[int, list[PRReviewThread]] = {}` to `__init__`
- Add implementation + setter:

```python
def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
    return self._review_threads_by_pr.get(pr_number, [])

def set_review_threads(self, pr_number: int, threads: list[PRReviewThread]) -> None:
    self._review_threads_by_pr[pr_number] = threads
```

Add import: `from erk_shared.gateway.github.types import PRReviewThread`

## Step 4: Create UnresolvedCommentsScreen

**File:** `src/erk/tui/screens/unresolved_comments_screen.py` (NEW)

Follow `IssueBodyScreen` pattern exactly:

- `ModalScreen` subclass with `BINDINGS` (escape, q, space → dismiss)
- `DEFAULT_CSS` matching IssueBodyScreen's dialog sizing/styling (90% width, 80% height)
- `__init__` takes: `provider: PlanDataProvider`, `pr_number: int`, `full_title: str`, `resolved_count: int`, `total_count: int`
- `compose()` yields: header (title + count summary), divider, scrollable container with loading label, footer
- `on_mount()` triggers `_fetch_comments()`
- `@work(thread=True) _fetch_comments()` calls `provider.fetch_unresolved_comments(pr_number)`, catches exceptions, calls `app.call_from_thread(self._on_loaded, ...)`
- `_on_loaded()` removes loading label, mounts `Markdown` widget with formatted content

**Formatting each thread as markdown:**
```
### `path/to/file.py:42`
**author** · 2025-01-15

comment body text here

---
```

The `_format_threads()` method converts `list[PRReviewThread]` to a markdown string. For each thread, show the first comment's body (the review comment) and indicate if there are follow-up replies (e.g., "+ 2 replies").

## Step 5: Add key binding and action in app.py

**File:** `src/erk/tui/app.py`

Add binding to `BINDINGS` list (after the `c` removal comment):
```python
Binding("c", "view_comments", "Comments", show=False),
```

Add action method:
```python
def action_view_comments(self) -> None:
    """Display unresolved PR review comments in a modal."""
    row = self._get_selected_row()
    if row is None:
        return
    if row.pr_number is None:
        if self._status_bar is not None:
            self._status_bar.set_message("No PR linked to this plan")
        return
    unresolved = row.total_comment_count - row.resolved_comment_count
    if unresolved == 0:
        if self._status_bar is not None:
            self._status_bar.set_message("No unresolved comments")
        return
    self.push_screen(
        UnresolvedCommentsScreen(
            provider=self._provider,
            pr_number=row.pr_number,
            full_title=row.full_title,
            resolved_count=row.resolved_comment_count,
            total_count=row.total_comment_count,
        )
    )
```

Add import for `UnresolvedCommentsScreen`.

## Step 6: Update HelpScreen

**File:** `src/erk/tui/screens/help_screen.py`

Add to the "Actions" section (after the `i` binding line):
```python
yield Label("c       View unresolved comments", classes="help-binding")
```

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` | Add `fetch_unresolved_comments` abstract method |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Implement via `self._ctx.github.get_pr_review_threads()` |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` | Implement with dict storage + setter |
| `src/erk/tui/screens/unresolved_comments_screen.py` | NEW: modal screen |
| `src/erk/tui/app.py` | Add `c` binding + `action_view_comments` |
| `src/erk/tui/screens/help_screen.py` | Add `c` to help text |

## Verification

1. **Type check**: Run `ty` to verify all ABC implementations are complete
2. **Unit tests**: Run existing TUI tests to ensure nothing breaks
3. **Manual test**: `erk dash -i`, navigate to a plan with unresolved comments (comments column shows e.g. "1/4"), press `c`, verify modal appears with thread details
4. **Edge cases**: Test `c` on row with no PR (status bar message), row with 0 unresolved (status bar message), row with PR but API error (error shown in modal)