# Fix `erk plan duplicate-check` to evaluate against all open plans

## Context

`erk plan duplicate-check --plan 8022` only checks against 6 plans, but `erk plan list` shows 30 open plans. The user expects duplicate-check to evaluate against all open plans.

**Root Cause:** The duplicate-check command uses `ctx.plan_store.list_plans()` which routes to `DraftPRPlanBackend.list_plans()`. That method calls `self._github.list_prs(draft=True)`, filtering to only **draft** PRs. Plans in `impl` stage have been undrafted (converted from draft to regular PRs for CI), so they're invisible. Only the 6 plans still in draft state (planned/planning/prompted) appear.

Meanwhile, `erk plan list` uses `ctx.plan_list_service.get_plan_list_data()` via `DraftPRPlanListService`, which calls `list_plan_prs_with_details()` - a GraphQL query that returns ALL PRs with the `erk-plan` label regardless of draft status.

## Plan

### 1. Update `duplicate_check_cmd.py` to use `plan_list_service`

**File:** `src/erk/cli/commands/plan/duplicate_check_cmd.py`

Replace the `ctx.plan_store.list_plans()` call (lines 92-96) with `ctx.plan_list_service.get_plan_list_data()`:

```python
# Before (only gets draft PRs):
existing_plans = ctx.plan_store.list_plans(
    repo_root,
    PlanQuery(state=PlanState.OPEN),
)

# After (gets ALL open plan PRs):
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

repo = discover_repo_context(ctx, ctx.cwd)  # already called above
if repo.github is None:
    user_output(click.style("Error: ", fg="red") + "Could not determine repository owner/name")
    raise SystemExit(1)

location = GitHubRepoLocation(
    root=repo_root,
    repo_id=GitHubRepoId(repo.github.owner, repo.github.repo),
)
plan_data = ctx.plan_list_service.get_plan_list_data(
    location=location,
    labels=["erk-plan"],
    state="open",
    skip_workflow_runs=True,
)
existing_plans = plan_data.plans
```

Also remove unused imports: `PlanQuery`, `PlanState` (no longer needed for listing).

### 2. Update tests to wire up `plan_list_service`

**File:** `tests/commands/plan/test_duplicate_check.py`

Tests currently use `create_plan_store_with_plans()` which creates a `GitHubPlanStore` (issue-based, not draft-PR-based). Since the command will now use `plan_list_service` for listing (but still `plan_store` for `get_plan()`), we need to wire up `FakePlanListService` with the plans.

- Import `FakePlanListService` and `PlanListData`
- Create a helper that builds both `plan_store` (for `--plan` flag lookups) and `plan_list_service` (for listing)
- Update each test to pass `plan_list_service=...` to `build_workspace_test_context()`

## Key Files

- `src/erk/cli/commands/plan/duplicate_check_cmd.py` - command implementation
- `tests/commands/plan/test_duplicate_check.py` - tests
- `packages/erk-shared/src/erk_shared/core/fakes.py:259` - `FakePlanListService`
- `packages/erk-shared/src/erk_shared/core/plan_list_service.py` - `PlanListData`, `PlanListService`

## Verification

1. Run existing tests: `pytest tests/commands/plan/test_duplicate_check.py`
2. Run checker tests: `pytest tests/core/test_plan_duplicate_checker.py`
3. Manual test: `erk plan duplicate-check --plan 8022` should now show all 30 open plans
