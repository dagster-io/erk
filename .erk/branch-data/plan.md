# Add ObjectiveListService Abstraction

## Context

The TUI dashboard currently fetches objectives (GitHub issues with `erk-objective` label) via a hack in `RealPlanDataProvider.__init__`: it manually constructs a `RealPlanListService` instance (`_issue_plan_list_service`) to bypass the `DraftPRPlanListService` that may be configured when `ERK_PLAN_BACKEND=draft_pr`. The `fetch_plans()` method then checks `if "erk-plan" in filters.labels` to route between the two services.

This leaks implementation details (objectives = GitHub issues with a specific label) throughout the TUI layer. The fix is a proper `ObjectiveListService` abstraction — symmetric with `PlanListService` — that encapsulates that knowledge.

## Approach

Create `ObjectiveListService` ABC (in `erk_shared`) with a single `get_objective_list_data()` method that has no `labels` parameter (encapsulated). Add `RealObjectiveListService` (in `erk`) that wraps `RealPlanListService` with hardcoded `labels=["erk-objective"]`. Add `FakeObjectiveListService` to `fakes.py`. Wire `objective_list_service` into `ErkContext` and remove the hack from `RealPlanDataProvider`.

Return type reuses `PlanListData` — objectives are plan-like objects and the TUI converts both to `PlanRowData` identically.

## Files to Create

### `packages/erk-shared/src/erk_shared/core/objective_list_service.py`

New ABC, parallel to `plan_list_service.py`:

```python
class ObjectiveListService(ABC):
    @abstractmethod
    def get_objective_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        state: str | None,
        limit: int | None,
        skip_workflow_runs: bool,
        creator: str | None,
    ) -> PlanListData: ...
```

No `labels` parameter — the implementation knows it fetches `erk-objective` items.

### `src/erk/core/services/objective_list_service.py`

`RealObjectiveListService` wraps `RealPlanListService` with `labels=["erk-objective"]`:

```python
class RealObjectiveListService(ObjectiveListService):
    def __init__(self, github: GitHub, github_issues: GitHubIssues) -> None:
        self._plan_list_service = RealPlanListService(github, github_issues)

    def get_objective_list_data(self, *, location, state, limit, skip_workflow_runs, creator) -> PlanListData:
        return self._plan_list_service.get_plan_list_data(
            location=location,
            labels=["erk-objective"],
            state=state, limit=limit,
            skip_workflow_runs=skip_workflow_runs,
            creator=creator,
        )
```

## Audit Findings: All Objective List Fetches

Beyond the TUI hack, there is one other production location that fetches a list of objectives directly via GitHub issues:

**`src/erk/cli/commands/objective/list_cmd.py`** — calls `ctx.issues.list_issues(repo_root=repo.root, labels=["erk-objective"], state="open")` then accesses `issue.number`, `issue.title`, `issue.created_at`, `issue.url`.

All other objective references are: single-issue fetches (get by number), mutations (create/update/close), or plan fetches that _reference_ objectives — not objective list fetches. Those don't need `ObjectiveListService`.

The CLI `list_cmd.py` should also be migrated. It needs `GitHubRepoLocation` constructed from `ctx.repo_info` and `repo.root`, then calls `ctx.objective_list_service.get_objective_list_data(location=..., state="open", limit=None, skip_workflow_runs=True, creator=None)`. The `Plan` objects in `plan_data.plans` have all the fields the command needs (`.plan_identifier`, `.title`, `.created_at`, `.url`).

## Files to Modify

### `packages/erk-shared/src/erk_shared/core/fakes.py`

Add `FakeObjectiveListService` alongside `FakePlanListService` (line 258):

- Add import for `ObjectiveListService` from `erk_shared.core.objective_list_service`
- Add class that returns pre-configured `PlanListData` (default: empty)

### `packages/erk-shared/src/erk_shared/context/context.py`

- Add import: `from erk_shared.core.objective_list_service import ObjectiveListService`
- Add field to `ErkContext` after `plan_list_service` (line 98):
  ```python
  plan_list_service: PlanListService
  objective_list_service: ObjectiveListService
  ```
- Update module docstring to mention `ObjectiveListService`

### `packages/erk-shared/src/erk_shared/context/testing.py`

- Add `FakeObjectiveListService` to the imports from `erk_shared.core.fakes` (line 18)
- Add `objective_list_service=FakeObjectiveListService()` to the `ErkContext(...)` constructor call at line 212 (alongside `plan_list_service=FakePlanListService()`)

### `src/erk/core/context.py`

Three locations to update:

1. **`create_context()`** — after `plan_list_service` is assigned in the `if/else` block, add:
   ```python
   objective_list_service: ObjectiveListService = RealObjectiveListService(github, issues)
   ```
   Pass to `ErkContext(...)`.
2. **`minimal_context()`** — add `objective_list_service=FakeObjectiveListService()` to `ErkContext(...)`.
3. **`context_for_test()`** — add optional `objective_list_service: ObjectiveListService | None = None` parameter; default to `RealObjectiveListService(github, issues)` mirroring how `plan_list_service` defaults.

### `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

This is the primary cleanup. Three changes:

1. **Remove** the import of `RealPlanListService` from `erk.core.services.plan_list_service` (line 17) — eliminates a `packages/erk-shared` → `src/erk/` import dependency
2. **Remove** `self._issue_plan_list_service = RealPlanListService(...)` from `__init__` (line 104)
3. **Replace** the routing logic in `fetch_plans()` (lines 136–151):

   ```python
   # Before (hack):
   if "erk-plan" in filters.labels:
       plan_list_service = self._ctx.plan_list_service
   else:
       plan_list_service = self._issue_plan_list_service
   plan_data = plan_list_service.get_plan_list_data(location=..., labels=list(filters.labels), ...)

   # After (clean):
   if "erk-plan" in filters.labels:
       plan_data = self._ctx.plan_list_service.get_plan_list_data(
           location=self._location, labels=list(filters.labels),
           state=filters.state, limit=filters.limit,
           skip_workflow_runs=not needs_workflow_runs, creator=filters.creator,
       )
   else:
       plan_data = self._ctx.objective_list_service.get_objective_list_data(
           location=self._location,
           state=filters.state, limit=filters.limit,
           skip_workflow_runs=not needs_workflow_runs, creator=filters.creator,
       )
   ```

### `src/erk/cli/commands/objective/list_cmd.py`

Migrate from `ctx.issues.list_issues()` to `ctx.objective_list_service`:

1. Remove `ctx.issues.list_issues(labels=["erk-objective"], ...)` call
2. Add guard: `if ctx.repo_info is None: raise click.ClickException("Not in a GitHub repository")`
3. Construct `GitHubRepoLocation(root=repo.root, repo_id=GitHubRepoId(owner=ctx.repo_info.owner, repo=ctx.repo_info.name))`
4. Call `ctx.objective_list_service.get_objective_list_data(location=..., state="open", limit=None, skip_workflow_runs=True, creator=None)`
5. Iterate `plan_data.plans` instead of `issues` — use `int(plan.plan_identifier)` for number, `plan.title`, `plan.created_at`, `plan.url`

## New Test File

### `tests/unit/services/test_objective_list_service.py`

Tests for `RealObjectiveListService`:

- Verifies it delegates to `RealPlanListService` with `labels=["erk-objective"]`
- Verifies `state`, `limit`, `creator`, `skip_workflow_runs` are forwarded
- Uses `FakeGitHub` / `FakeGitHubIssues` from existing test infrastructure

## Verification

1. Run TUI tests: `pytest tests/tui/ -x` — should pass (220 tests)
2. Run context/services tests: `pytest tests/unit/services/ tests/unit/context/ -x`
3. Run type checker: `ty check packages/erk-shared/src/erk_shared/core/ src/erk/core/`
4. Manual smoke test: launch TUI, switch to Objectives view (key 3), verify objectives load
5. Test with `ERK_PLAN_BACKEND=draft_pr` env var set — objectives must still load in TUI

## Key Reused Functions / Patterns

- `RealPlanListService` (`src/erk/core/services/plan_list_service.py`) — wrapped by the real implementation
- `PlanListData` (`packages/erk-shared/src/erk_shared/core/plan_list_service.py`) — reused as return type
- `FakePlanListService` (`packages/erk-shared/src/erk_shared/core/fakes.py:258`) — template for `FakeObjectiveListService`
- `context_for_test()` in `src/erk/core/context.py` — template for adding the new optional param
