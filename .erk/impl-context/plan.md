# Plan: Targeted plan fetching by issue number for objective plans modal

## Context

The ObjectivePlansScreen modal shows plans linked to an objective, but currently uses broad list queries (fetch_plans with limit=200) and filters client-side. With 3,538+ closed erk-plan issues, limit=200 misses most closed plans — causing the modal to show only 1 plan for objective #8036 despite 6 roadmap-referenced plans.

The fix: extract plan IDs from the objective's roadmap frontmatter (already done), then fetch ONLY those specific issues by number using a batched GraphQL query. No more listing all plans and filtering.

Key discovery: Must use issueOrPullRequest(number: N) instead of issue(number: N) because some plans (#8070, #8087, etc.) are merged PRs, not issues.

## Changes

### 1. GitHub Gateway — get_issues_by_numbers_with_pr_linkages

New method to fetch specific issues by number with full PR linkage data.

`packages/erk-shared/src/erk_shared/gateway/github/abc.py` — Add abstract method:
```python
@abstractmethod
def get_issues_by_numbers_with_pr_linkages(
    self,
    *,
    location: GitHubRepoLocation,
    issue_numbers: list[int],
) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
```

`packages/erk-shared/src/erk_shared/gateway/github/real.py` — Implement with batched alias query:
- New private method `_build_issues_by_numbers_query(issue_numbers, repo_id)` — builds GraphQL query using aliases (same pattern as existing `_build_issue_pr_linkage_query` at line 688, but includes full issue fields: title, body, state, url, author, labels, assignees, createdAt, updatedAt, plus timeline/PR linkages)
- New private method `_parse_issues_by_numbers_response(response, repo_id)` — iterates over aliased keys (issue_8070, etc.), reuses existing `_parse_issue_node` and `_parse_pr_from_timeline_event` per node
- Main method: handle empty list → ([], {}), else build query → execute_gh_command_with_retry → parse response
- The ISSUE_PR_LINKAGE_FRAGMENT from graphql_queries.py is reused for the timeline fields

`packages/erk-shared/src/erk_shared/gateway/github/fake.py` — Filter self._issues_data by number, build matching pr_linkages subset

`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` — Delegate to self._wrapped

`packages/erk-shared/src/erk_shared/gateway/github/printing.py` — Delegate to self._wrapped

### 2. PlanDataProvider — fetch_plans_by_ids

`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` — Add abstract method:
```python
@abstractmethod
def fetch_plans_by_ids(self, plan_ids: set[int]) -> list[PlanRowData]:
```

`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — Implement:
- Call `self._ctx.github.get_issues_by_numbers_with_pr_linkages(location=self._location, issue_numbers=list(plan_ids))`
- Convert each IssueInfo → Plan via `issue_info_to_plan()` (import from `erk_shared.plan_store.conversion`)
- Build worktree mapping via `self._build_worktree_mapping()`
- Batch fetch learn issue states via `self._fetch_learn_issue_states()`
- Call `self._build_row_data()` for each plan (pass workflow_run=None)
- Return sorted by plan_id

`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` — Filter:
```python
def fetch_plans_by_ids(self, plan_ids: set[int]) -> list[PlanRowData]:
    return [p for p in self._plans if p.plan_id in plan_ids]
```

### 3. Screen — Simplify _fetch_plans

`src/erk/tui/screens/objective_plans_screen.py` — Replace the current fetch with:
```python
@work(thread=True)
def _fetch_plans(self) -> None:
    plans: list[PlanRowData] = []
    error: str | None = None
    try:
        roadmap_plan_ids = _extract_plan_ids_from_roadmap(self._objective_body)
        if roadmap_plan_ids:
            plans = self._provider.fetch_plans_by_ids(roadmap_plan_ids)
        else:
            plans = self._provider.fetch_plans_for_objective(self._objective_id)
    except Exception as e:
        error = str(e)
    self.app.call_from_thread(self._on_plans_loaded, plans, error)
```

### 4. Tests

`tests/tui/screens/test_objective_plans_screen.py` — Update test_roadmap_based_plan_discovery:
- The test currently relies on fetch_plans_for_objective + fetch_plans calls
- After the change, it uses fetch_plans_by_ids on the fake, which filters by plan_id
- Existing tests for empty state, error state, and non-roadmap paths still pass

## Verification

1. devrun: `uv run ruff check` on all changed files
2. devrun: `uv run ty check` on all changed files
3. devrun: `uv run pytest tests/tui/screens/test_objective_plans_screen.py -x`
4. devrun: `uv run pytest tests/tui/ -x`
