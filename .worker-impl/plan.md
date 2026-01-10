# Plan: Fetch Plan Body On-Demand via REST

## Problem

The "v" key binding currently shows the issue body (metadata), but the actual plan content is stored in the **first comment** of the GitHub issue.

## Solution

Fetch the plan content on-demand when the user presses "v", using the REST API to get the first comment.

## Implementation Steps

### Phase 1: Add Comment Fetching to PlanDataProvider

**File: `src/erk/tui/data/provider.py`**

Add method to `PlanDataProvider` ABC and `RealPlanDataProvider`:
```python
def fetch_plan_content(self, issue_number: int) -> str | None:
    """Fetch plan content from the first comment of an issue."""
```

Implementation uses existing GitHub REST API to:
1. Get comments for the issue: `GET /repos/{owner}/{repo}/issues/{issue_number}/comments`
2. Take first comment body
3. Extract plan content using `extract_plan_from_comment()`

### Phase 2: Update IssueBodyScreen for Async Loading

**File: `src/erk/tui/app.py`**

Modify `IssueBodyScreen` to:
1. Accept `provider` and `issue_number` instead of pre-loaded content
2. Show loading state initially
3. Fetch content asynchronously using `run_worker()`
4. Display content when loaded, or error message if fetch fails

### Phase 3: Update action_view_issue_body

**File: `src/erk/tui/app.py`**

Pass provider and issue number to `IssueBodyScreen` instead of the row's body.

### Phase 4: Remove issue_body from PlanRowData

**File: `src/erk/tui/data/types.py`**

Remove `issue_body` field since we no longer pre-load it.

### Phase 5: Update Fakes and Tests

- **`tests/fakes/plan_data_provider.py`**: Add `fetch_plan_content()` method to `FakePlanDataProvider`
- **`tests/tui/test_app.py`**: Update tests for async loading behavior

## Verification

1. Run `erk dash -i`, select a plan, press "v" - should show loading, then actual plan content
2. Run TUI tests: `uv run pytest tests/tui/ -v`
3. Run full CI: `make fast-ci`