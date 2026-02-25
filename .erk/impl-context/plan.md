# Make `http_client` a required parameter in plan list services

## Context

The PR on branch `plnd/http-dash-fetch-02-25-0823` introduced an optional `http_client: HttpClient | None` parameter to plan list service signatures. This plan makes `http_client` a **required** parameter (`HttpClient`, not `HttpClient | None`) everywhere it appears, removing the conditional routing (subprocess fallback) in `PlannedPRPlanListService`.

**Approach**: Accept `http_client` as unused in `RealPlanListService` (it will be deleted later). Do NOT port issue-based plans to HTTP.

## Changes

### 1. Update the ABC signature

**File**: `packages/erk-shared/src/erk_shared/core/plan_list_service.py`

- Line 21: Change the `TYPE_CHECKING` import of `HttpClient` to a regular import (move out of `if TYPE_CHECKING:` block)
- Line 65: Change `http_client: HttpClient | None` to `http_client: HttpClient`
- Update the docstring to remove the "optional" language

### 2. Update `FakePlanListService`

**File**: `packages/erk-shared/src/erk_shared/core/fakes.py`

- Line 278: Change `http_client: object | None` to `http_client: HttpClient` (note: currently uses `object | None`, not `HttpClient | None`)
- Add import for `HttpClient` from `erk_shared.gateway.http.abc`

### 3. Update `PlannedPRPlanListService`

**File**: `src/erk/core/services/plan_list_service.py`

- Line 70 (in `get_plan_list_data` signature): Change `http_client: HttpClient | None` to `http_client: HttpClient`
- Lines 91-101: **Remove** the `if http_client is not None:` conditional routing block. The method should always call `self._get_plan_list_data_http(http_client, ...)` directly. Delete the entire subprocess fallback path below the conditional (the code after the `if` block through line ~101, which was the `# Subprocess path: REST+GraphQL two-step via gh CLI` section).
- Update the docstring to remove "When http_client is provided" / "Falls back to subprocess path" language. The method now always uses HTTP.

**Important**: Keep the `_get_plan_list_data_http` private method as-is. Keep the `_fetch_workflow_runs_subprocess` method (it's still used within `_get_plan_list_data_http` — actually check: it may no longer be needed if `_fetch_workflow_runs_http` replaced it). Wait, re-reading the code: `_get_plan_list_data_http` calls `_fetch_workflow_runs_http`, not `_fetch_workflow_runs_subprocess`. So after removing the subprocess path from `get_plan_list_data`, the `_fetch_workflow_runs_subprocess` method and `_parse_pr_details` may become dead code IF they're only called from the subprocess path. Check for other callers before removing.

Actually, `_parse_pr_details` IS called from both paths (`_get_plan_list_data_http` line references `self._parse_pr_details`). Keep it. Check whether `_fetch_workflow_runs_subprocess` is called from `_get_plan_list_data_http` — if not, it can be removed along with the subprocess code from `get_plan_list_data`. The subprocess `list_plan_prs_with_details` call should also become unused from this class.

**Dead code removal**: After removing the conditional in `get_plan_list_data`:
- Remove `_fetch_workflow_runs_subprocess` method if only called from the deleted subprocess path
- Remove any now-unused imports (e.g., if `list_plan_prs_with_details` was only used in the subprocess path)

### 4. Update `RealPlanListService`

**File**: `src/erk/core/services/plan_list_service.py`

- Line 372 (in `get_plan_list_data` signature): Change `http_client: HttpClient | None` to `http_client: HttpClient`
- Update docstring for `http_client` parameter: keep the "Unused for issue-based plans" note but change type description
- The method body does not reference `http_client` so no logic changes needed

### 5. Update `RealObjectiveListService` call site

**File**: `src/erk/core/services/objective_list_service.py`

- Line 26: Add `http_client: HttpClient` as a constructor parameter to `RealObjectiveListService.__init__`
- Store it as `self._http_client`
- Line 47: Change `http_client=None` to `http_client=self._http_client`
- Add import for `HttpClient` from `erk_shared.gateway.http.abc`

### 6. Update `RealPlanDataProvider` to pass `http_client` to `ObjectiveListService`

**File**: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Line 133: Remove the `supports_direct_api` filter. Instead of `http_for_service = self._http_client if self._http_client.supports_direct_api else None`, just pass `self._http_client` directly to `get_plan_list_data`.
- Line 154: Change `http_client=http_for_service` to `http_client=self._http_client`
- Remove the `http_for_service` local variable entirely

**Note**: The `supports_direct_api` check was needed when `None` meant "fall back to subprocess." Now that the parameter is always required, the service implementations decide how to use it internally. `RealPlanListService` ignores it, and `PlannedPRPlanListService` always uses the HTTP path. The caller no longer needs to pre-filter.

### 7. Update `ObjectiveListService` ABC to accept `http_client`

**Wait** — re-examining the prompt: The `ObjectiveListService` ABC at `packages/erk-shared/src/erk_shared/core/objective_list_service.py` does NOT have an `http_client` parameter in `get_objective_list_data`. The call in `RealPlanDataProvider.fetch_plans` (line 137-144) calls `get_objective_list_data` without `http_client`. The `http_client` is threaded through `RealObjectiveListService` as a constructor parameter and passed internally to `RealPlanListService.get_plan_list_data`.

So `ObjectiveListService` ABC does NOT need changes. The `http_client` flows through the constructor, not the method parameter. This is correct.

### 8. Update `ErkContext` or wherever `RealObjectiveListService` is constructed

Find where `RealObjectiveListService` is instantiated and pass `http_client` to its new constructor parameter.

**Search needed by implementor**: Grep for `RealObjectiveListService(` to find all construction sites. The implementor will need to thread `http_client` through from wherever `ErkContext` is built.

### 9. Update `duplicate_check_cmd.py`

**File**: `src/erk/cli/commands/pr/duplicate_check_cmd.py`

- Line 115: Change `http_client=None` to pass a real `HttpClient` instance
- Create a `RealHttpClient` using `fetch_github_token()`:
  ```python
  from erk_shared.gateway.http.auth import fetch_github_token
  from erk_shared.gateway.http.real import RealHttpClient

  http_client = RealHttpClient(token=fetch_github_token(), base_url="https://api.github.com")
  ```
- Actually — `duplicate_check_cmd` calls `ctx.plan_list_service.get_plan_list_data(...)`. The `ctx.plan_list_service` could be `RealPlanListService` (which ignores `http_client`) or `PlannedPRPlanListService` (which uses it for HTTP). Since this command checks both `erk-planned-pr` and `erk-plan` labels, it might hit either service. The safest approach is to create a `RealHttpClient` and pass it.
- Add the necessary imports at the top of the file

### 10. Update all tests — `http_client=None` → `http_client=FakeHttpClient()`

**File**: `tests/unit/services/test_plan_list_service.py`

20 occurrences of `http_client=None` at lines: 54, 98, 117, 160, 201, 268, 321, 349, 390, 435, 617, 631, 661, 700, 724, 768, 807, 850, 889, 922.

**Action**: Replace all `http_client=None` with `http_client=FakeHttpClient()` and add import:
```python
from erk_shared.gateway.http.fake import FakeHttpClient
```

Use a batch find-and-replace for this file since all occurrences are identical.

### 11. Verify no other `http_client=None` call sites exist

**Files already using `FakeHttpClient()` (no changes needed)**:
- `tests/tui/data/test_provider.py` — already uses `http_client=FakeHttpClient()` (22 instances)
- `tests/tui/data/test_fetch_plan_content.py` — already uses `FakeHttpClient` via `_make_provider` helper
- `tests/tui/data/test_fetch_objective_content.py` — already uses `FakeHttpClient` via `_make_provider` helper
- `tests/unit/services/test_plan_list_service_http.py` — already passes `FakeHttpClient` instances

**File with MagicMock**:
- `tests/erk_shared/gateway/plan_data_provider/test_real_routing.py` line 32: Uses `http_client=MagicMock()`. This should be fine since `MagicMock` satisfies any type at runtime.

**No changes needed**:
- `tests/commands/plan/test_duplicate_check.py` — does not directly reference `http_client` (uses `FakePlanListService` which handles it internally)
- `tests/integration/test_plan_repo_root.py` — does not reference `http_client`

### 12. Update `RealObjectiveListService` construction sites

The implementor must grep for `RealObjectiveListService(` to find all places it's instantiated. Each must now pass an `http_client` parameter. Expected locations:
- Wherever `ErkContext` is built (likely in CLI entrypoint or context factory)
- Any test that directly constructs `RealObjectiveListService`

For test construction sites, pass `FakeHttpClient()`. For production construction sites, pass the same `HttpClient` instance used elsewhere in the context.

## Files NOT changing

- `packages/erk-shared/src/erk_shared/core/objective_list_service.py` — The `ObjectiveListService` ABC does not expose `http_client` in its method signature. It flows via constructor.
- `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — `HttpClient` ABC unchanged
- `packages/erk-shared/src/erk_shared/gateway/http/real.py` — `RealHttpClient` unchanged
- `packages/erk-shared/src/erk_shared/gateway/http/fake.py` — `FakeHttpClient` unchanged
- `src/erk/cli/commands/pr/list_cmd.py` — already uses `FakeHttpClient()` and `RealHttpClient()` correctly
- `src/erk/cli/commands/exec/scripts/dash_data.py` — already uses `RealHttpClient()` correctly
- `tests/tui/data/test_provider.py` — already uses `FakeHttpClient()`
- `tests/tui/data/test_fetch_plan_content.py` — already uses `FakeHttpClient`
- `tests/tui/data/test_fetch_objective_content.py` — already uses `FakeHttpClient`
- `CHANGELOG.md` — never modify

## Implementation order

1. Update the ABC signature (`packages/erk-shared/.../plan_list_service.py`)
2. Update `FakePlanListService` (`packages/erk-shared/.../fakes.py`)
3. Update `PlannedPRPlanListService` and `RealPlanListService` (`src/erk/core/services/plan_list_service.py`)
4. Update `RealObjectiveListService` (`src/erk/core/services/objective_list_service.py`)
5. Find and update `RealObjectiveListService` construction sites
6. Update `RealPlanDataProvider` (`packages/erk-shared/.../real.py`)
7. Update `duplicate_check_cmd.py` (`src/erk/cli/commands/pr/duplicate_check_cmd.py`)
8. Update tests (`tests/unit/services/test_plan_list_service.py`)
9. Remove dead code from `PlannedPRPlanListService` (subprocess path, unused methods)

## Verification

1. Run `ty` (type checker) — all type errors should be resolved
2. Run `pytest tests/unit/services/test_plan_list_service.py` — all 20 test call sites updated
3. Run `pytest tests/unit/services/test_plan_list_service_http.py` — HTTP path tests still pass
4. Run `pytest tests/tui/data/` — TUI data provider tests still pass
5. Run `pytest tests/commands/plan/test_duplicate_check.py` — duplicate check tests still pass
6. Run `ruff check` and `ruff format --check` — no lint/format issues
7. Run full `pytest` to catch any missed call sites