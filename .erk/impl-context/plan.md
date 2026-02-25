# Continue: Replace gh subprocess with HTTP for dash Plans tab

## Context

Resuming implementation of plan #8193. Two of six tasks are complete:
- **Done**: Added `get_list()`, `graphql()`, `supports_direct_api` to HttpClient (all 5 places)
- **Done**: Extracted parsing functions to `pr_data_parsing.py`, updated all call sites in `real.py`

Remaining work: wire the HTTP path into PlannedPRPlanListService, pass http_client from provider, check ObjectiveListService, run CI.

## Remaining Steps

### Task 2: Mark complete
The extraction is verified done — no `self._parse_*` or `self._merge_rest_*` references remain in `real.py`.

### Task 3: Add HTTP path to PlannedPRPlanListService

**File:** `src/erk/core/services/plan_list_service.py`

- Add `http_client: HttpClient | None = None` param to `PlanListService.get_plan_list_data()` ABC and all implementations
- Add `_get_plan_list_data_http()` method to `PlannedPRPlanListService` that:
  1. REST: `http_client.get_list(f"repos/{owner}/{repo}/issues?labels=...&state=...&per_page=...&sort=updated&direction=desc&creator=...")`
  2. Filter to PRs (items with `pull_request` key), apply `exclude_labels` client-side
  3. Build enrichment GraphQL query (aliased `pullRequest(number: N)` fields) — reuse the same field shape from `_enrich_prs_via_graphql` in `real.py`
  4. `http_client.graphql(query=..., variables={"owner": ..., "repo": ...})`
  5. Merge via `merge_rest_graphql_pr_data()` from `pr_data_parsing.py`
  6. Workflow runs: `http_client.graphql(query=GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY, variables={"nodeIds": [...]})`
  7. Parse via `parse_workflow_runs_nodes_response()` from `pr_data_parsing.py`
- In `get_plan_list_data()`: if `http_client is not None`, call `_get_plan_list_data_http()`; otherwise fall back to existing subprocess path

**Also update:**
- `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — Add `http_client` param to ABC
- `packages/erk-shared/src/erk_shared/core/fakes.py` — Add param to `FakePlanListService` (ignored)
- `src/erk/core/services/plan_list_service.py` — Add param to `RealPlanListService` (ignored)

### Task 4: Pass http_client from provider to service

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

In `RealPlanDataProvider.fetch_plans()`, pass http_client when calling plan_list_service:
```python
http_for_service = self._http_client if self._http_client.supports_direct_api else None
plan_data = self._ctx.plan_list_service.get_plan_list_data(
    ...,
    http_client=http_for_service,
)
```

### Task 5: ObjectiveListService

**File:** `src/erk/core/services/objective_list_service.py`

`RealObjectiveListService` delegates to `RealPlanListService.get_plan_list_data()`. Since `RealPlanListService` ignores `http_client` (it uses `get_issues_with_pr_linkages` not subprocess PRs), no functional changes needed — just pass through the param for ABC compatibility.

### Task 6: CI verification

Run `make fast-ci` via devrun agent.

## Verification

1. `make fast-ci` passes (no regressions)
2. Existing tests for `PlannedPRPlanListService`, `RealPlanListService`, and `FakePlanListService` still pass
3. Type checker (`ty`) passes on modified files
