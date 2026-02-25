The current PR on branch `plnd/http-dash-fetch-02-25-0823` adds an optional `http_client: HttpClient | None` parameter to plan list services. Make `http_client` a required parameter (`HttpClient`, not `HttpClient | None`) everywhere it appears.

## Approach

Use option 2: accept `http_client` as unused in `RealPlanListService` (it will be deleted later). Do NOT port issue-based plans to HTTP.

## What needs to change

### 1. Update the ABC / service signatures
- Change `http_client: HttpClient | None` to `http_client: HttpClient` in `PlanListService` ABC and all implementations (`PlannedPRPlanListService`, `RealPlanListService`)
- Remove all `if http_client is not None` conditional routing in `PlannedPRPlanListService` — always use the HTTP path

### 2. Fix call sites that currently pass `None`
- `objective_list_service.py` (~line 47): Thread `http_client` through `ObjectiveListService` — add it as a constructor parameter and pass it when constructing `PlannedPRPlanListService`
- `duplicate_check_cmd.py` (~line 115): Create a `RealHttpClient` using `fetch_github_token()` and pass it
- `list_cmd.py` static mode: Already uses `FakeHttpClient()` — should be fine

### 3. Update all tests (~30 call sites)
- Replace `http_client=None` with `http_client=FakeHttpClient()` in all test files
- Import `FakeHttpClient` where needed

### 4. `RealPlanListService`
- Accept the `http_client` parameter but don't use it (it queries issues via GitHub gateway's GraphQL subprocess path, not HTTP)
- This is intentional — the service will be deleted later

