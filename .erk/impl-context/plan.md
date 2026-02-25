# Plan: Replace gh subprocess with HTTP for dash Plans tab

## Context

The `erk dash` Plans tab takes 3.7s per refresh in steady state, with the REST+GraphQL API calls accounting for 2.4s (65%). This is dominated by 3 `gh api` subprocess calls that each pay ~200-300ms process spawn overhead. Replacing these with direct HTTP via the existing `HttpClient` (httpx-based) should save ~600-900ms per refresh cycle.

Timing log shows:
- First fetch: `rest:2.5 wf:0.5 wt:0.1 rows:8.5 = 11.7s`
- Steady state: `rest:2.4 wf:0.5 rows:0.8 = 3.7s`

The 3 subprocess calls to eliminate (all in `PlannedPRPlanListService.get_plan_list_data()`):
1. `gh api repos/.../issues?...` — REST issues list (~1.2-1.5s)
2. `gh api graphql` — PR enrichment (~0.8-1.0s)
3. `gh api graphql` — workflow runs (~0.5s)

## Implementation

### Step 1: Add `get_list()` and `graphql()` to HttpClient

The REST issues endpoint returns a JSON **array**, but `HttpClient.get()` returns `dict[str, Any]`. Add two new methods:

**Files:**
- `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — Add abstract methods
- `packages/erk-shared/src/erk_shared/gateway/http/real.py` — Implement with httpx
- `packages/erk-shared/src/erk_shared/gateway/http/fake.py` — Implement for tests
- `packages/erk-shared/src/erk_shared/gateway/http/dry_run.py` — Implement (delegate to wrapped)
- `packages/erk-shared/src/erk_shared/gateway/http/printing.py` — Implement (delegate to wrapped)

```python
# abc.py additions
@abstractmethod
def get_list(self, endpoint: str) -> list[dict[str, Any]]:
    """GET endpoint returning a JSON array."""
    ...

@abstractmethod
def graphql(self, *, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Execute a GraphQL query via POST /graphql."""
    ...
```

```python
# real.py - graphql implementation
def graphql(self, *, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    url = f"{self._base_url}/graphql"
    payload = {"query": query, "variables": variables}
    response = httpx.post(url, json=payload, headers=self._build_headers(), timeout=30.0)
    if response.status_code >= 400:
        raise HttpError(...)
    return response.json()
```

### Step 2: Extract parsing functions from RealGitHub to shared module

The PR enrichment response parsing functions on `RealGitHub` don't use `self` state — they're pure data transformations. Extract them so both the subprocess path and HTTP path can share them.

**Source:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- `_parse_status_rollup()` (line 1303) — pure function
- `_parse_mergeable_status()` (line 1333) — pure function
- `_parse_review_thread_counts()` (line 1341) — pure function
- `_merge_rest_graphql_pr_data()` (line 1881) — calls the above 3
- `_parse_workflow_runs_nodes_response()` (line 1057) — pure function

**Target:** `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py` (new file)

Move these to module-level functions. Have `RealGitHub` call the extracted functions (backward compatible, no behavior change). Use the existing `parsing.py` pattern as a model.

### Step 3: Add HTTP path to PlannedPRPlanListService

Thread `http_client` through the PlanListService ABC to `PlannedPRPlanListService`.

**Files:**
- `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — Add `http_client: HttpClient | None = None` param to ABC
- `src/erk/core/services/plan_list_service.py` — Implement HTTP path in PlannedPRPlanListService, add param to RealPlanListService (ignored)
- `packages/erk-shared/src/erk_shared/core/fakes.py` — Add param to FakePlanListService (ignored)

In `PlannedPRPlanListService.get_plan_list_data()`:
```python
def get_plan_list_data(self, *, ..., http_client: HttpClient | None = None) -> PlanListData:
    if http_client is not None:
        return self._get_plan_list_data_http(http_client, ...)
    # Existing subprocess path unchanged
    ...
```

The `_get_plan_list_data_http()` method:
1. REST: `http_client.get_list(f"repos/{owner}/{repo}/issues?labels=...&state=...&per_page=...")`
2. Filter to PRs (items with `pull_request` key), apply exclude_labels
3. GraphQL PR enrichment: `http_client.graphql(query=ENRICHMENT_QUERY, variables={...})`
4. Merge via extracted `merge_rest_graphql_pr_data()` function
5. GraphQL workflow runs: `http_client.graphql(query=WORKFLOW_QUERY, variables={...})`
6. Parse via extracted `parse_workflow_runs_nodes_response()` function
7. Return PlanListData with timing breakdown

The GraphQL queries are already defined as constants in `packages/erk-shared/src/erk_shared/gateway/github/queries.py` — reuse them directly.

### Step 4: Pass http_client from provider to service

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

In `RealPlanDataProvider.fetch_plans()`, pass `self._http_client` through:
```python
plan_data = self._ctx.plan_list_service.get_plan_list_data(
    location=self._location,
    labels=list(filters.labels),
    ...,
    http_client=self._http_client,  # NEW
)
```

When the provider has a `RealHttpClient` (TUI/dash), the service uses HTTP. When it has a `FakeHttpClient` (static list mode), http_client still gets passed but won't have configured responses — need to handle gracefully by falling back to subprocess path.

**Fallback logic in PlannedPRPlanListService:** Check if http_client has the `graphql` method (duck typing), or simpler: wrap the HTTP path in try/except and fall back to subprocess on any error. Or: check `isinstance(http_client, FakeHttpClient)` — no, that violates abstraction. Cleanest: always try HTTP when http_client is not None, catch HttpError and fall back.

Actually, simplest: only pass `http_client` when it's a real client. In `RealPlanDataProvider`, track whether the http_client is real:

```python
# In fetch_plans():
# Only pass http_client for HTTP-accelerated path when we have a real client
# The check: RealHttpClient sets token/base_url, FakeHttpClient doesn't
http_for_service = self._http_client if hasattr(self._http_client, '_token') else None
```

No — that's fragile. Better approach: **add a property to HttpClient**:

```python
# abc.py
@property
def supports_direct_api(self) -> bool:
    """Whether this client can make real API calls (vs test fake)."""
    return False

# real.py - override to return True
@property
def supports_direct_api(self) -> bool:
    return True
```

Then: `http_for_service = self._http_client if self._http_client.supports_direct_api else None`

### Step 5: Update ObjectiveListService

**File:** `src/erk/core/services/objective_list_service.py`

The `RealObjectiveListService` wraps `RealPlanListService` and calls its `get_plan_list_data()`. Add `http_client` parameter passthrough to its own `get_objective_list_data()` method, or at minimum ensure it's compatible with the updated ABC.

Check: Does `ObjectiveListService` extend `PlanListService`? If yes, it needs the param. If it's a separate ABC, it may not need changes.

### Step 6: Update timing labels

Since HTTP combines what was 2 subprocess calls (REST + GraphQL enrichment) into faster in-process calls, the timing breakdown in `FetchTimings` may need adjustment. The `rest_issues_ms` field should still measure the same logical phase (API data fetching). No structural changes needed — just ensure the timings are captured correctly in the HTTP path.

## Files Modified

1. `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — Add get_list, graphql, supports_direct_api
2. `packages/erk-shared/src/erk_shared/gateway/http/real.py` — Implement new methods
3. `packages/erk-shared/src/erk_shared/gateway/http/fake.py` — Implement new methods
4. `packages/erk-shared/src/erk_shared/gateway/http/dry_run.py` — Implement new methods
5. `packages/erk-shared/src/erk_shared/gateway/http/printing.py` — Implement new methods
6. `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py` — NEW: extracted parsing functions
7. `packages/erk-shared/src/erk_shared/gateway/github/real.py` — Call extracted functions
8. `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — Add http_client param to ABC
9. `src/erk/core/services/plan_list_service.py` — HTTP path in PlannedPRPlanListService
10. `packages/erk-shared/src/erk_shared/core/fakes.py` — Add param to FakePlanListService
11. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — Pass http_client through
12. `src/erk/core/services/objective_list_service.py` — Passthrough if needed

## Verification

1. Run existing tests: `make fast-ci` to ensure no regressions
2. Run `erk dash -i` and observe timing breakdown in status bar
3. Compare before/after in `.erk/scratch/dash-timings.log`
4. Expected: steady-state rest drops from ~2.4s to ~1.5-1.8s (saving ~600-900ms subprocess overhead)
5. Verify `erk pr list` (static mode) still works correctly (falls back to subprocess path)
