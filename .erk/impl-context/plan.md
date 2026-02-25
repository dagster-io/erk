# Make `http_client` a Required Parameter in Plan List Services

## Context

The PR on branch `plnd/http-dash-fetch-02-25-0823` introduced an optional `http_client: HttpClient | None` parameter to plan list service signatures. This was a transitional step. Now we make `http_client` a **required** parameter (`HttpClient`, not `HttpClient | None`) everywhere it appears, and remove the conditional None-checking routing logic.

**Approach**: Accept `http_client` as unused in `RealPlanListService` (it will be deleted later). Do NOT port issue-based plans to HTTP.

## Changes

### 1. ABC signature: `packages/erk-shared/src/erk_shared/core/plan_list_service.py`

**Line 65**: Change the abstract method signature from:
```python
http_client: HttpClient | None,
```
to:
```python
http_client: HttpClient,
```

Also update the `TYPE_CHECKING` import to a regular import (line 21-22), since `HttpClient` is now used in the runtime signature:
```python
from erk_shared.gateway.http.abc import HttpClient
```
Remove the `if TYPE_CHECKING:` guard around this import.

### 2. `PlannedPRPlanListService`: `src/erk/core/services/plan_list_service.py`

**Line 70**: Change parameter from `http_client: HttpClient | None` to `http_client: HttpClient`.

**Lines 91-101**: Remove the `if http_client is not None:` conditional. The method should **always** use the HTTP path. Delete the entire subprocess fallback path (lines 103-130) and inline the HTTP path as the only path. Specifically:
- Remove the `if http_client is not None:` check
- Call `self._get_plan_list_data_http(http_client, ...)` unconditionally
- Delete the subprocess path code block (lines 103-130) that calls `self._github.list_plan_prs_with_details()`

Also delete the now-unused `_fetch_workflow_runs_subprocess` method (lines 320-339) since the subprocess path is removed.

Also update the `TYPE_CHECKING` import (lines 38-39) to a regular import:
```python
from erk_shared.gateway.http.abc import HttpClient
```

### 3. `RealPlanListService`: `src/erk/core/services/plan_list_service.py`

**Line 372**: Change parameter from `http_client: HttpClient | None` to `http_client: HttpClient`.

The parameter is intentionally accepted but unused — this service queries issues via GitHub gateway's GraphQL subprocess path, not HTTP. It will be deleted later. Update the docstring to note this.

### 4. `FakePlanListService`: `packages/erk-shared/src/erk_shared/core/fakes.py`

**Line 278**: Change parameter from `http_client: object | None` to `http_client: HttpClient` (using the proper type).

Add the import:
```python
from erk_shared.gateway.http.abc import HttpClient
```
This may need to be a `TYPE_CHECKING` import or regular import depending on whether it's used at runtime. Since it's in a method signature with `from __future__ import annotations`, a `TYPE_CHECKING` import is fine. Check the file's existing import style and match it.

### 5. `RealPlanDataProvider`: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

**Lines 131-133**: Remove the conditional routing logic:
```python
# REMOVE THIS:
http_for_service = self._http_client if self._http_client.supports_direct_api else None
```

Replace with always passing `self._http_client`:
```python
http_client=self._http_client,
```

This means line 154 changes from `http_client=http_for_service,` to `http_client=self._http_client,`.

### 6. `RealObjectiveListService`: `src/erk/core/services/objective_list_service.py`

**Line 47**: Change `http_client=None` to pass a real `HttpClient`. This requires threading `http_client` through as a constructor parameter.

Changes:
- Add `http_client: HttpClient` as a constructor parameter (keyword-only after `time`)
- Store as `self._http_client`
- Pass `http_client=self._http_client` at line 47 instead of `http_client=None`
- Add import: `from erk_shared.gateway.http.abc import HttpClient` (use `TYPE_CHECKING` guard)

Update caller in `src/erk/core/context.py`:
- **Line 618-620** (`create_context`): Thread `http_client` when creating `RealObjectiveListService`. Create an `HttpClient` instance. Since the objective list service uses `RealPlanListService` which accepts but ignores `http_client`, passing a `FakeHttpClient()` would also work. However, for consistency:
  - Import `FakeHttpClient` from `erk_shared.gateway.http.fake`
  - Pass `http_client=FakeHttpClient()` since `RealPlanListService` ignores it anyway

  **Alternative (simpler)**: Since `RealPlanListService.get_plan_list_data` ignores the `http_client` parameter entirely, we can pass a `FakeHttpClient()` in the objective list service to satisfy the type. This avoids needing the real token/HTTP setup for a parameter that's unused.

- **Line 370** (`context_for_test`): Also thread `http_client=FakeHttpClient()` when creating `RealObjectiveListService` at line 370.

- **Line 27** (`minimal_context`): The `RealObjectiveListService` created at line 27 needs `http_client` too. Pass `FakeHttpClient()`.

Wait — `minimal_context` doesn't create `RealObjectiveListService`. It uses `FakeObjectiveListService`. So no change needed there.

### 7. `duplicate_check_cmd.py`: `src/erk/cli/commands/pr/duplicate_check_cmd.py`

**Line 115**: Change `http_client=None` to create a `RealHttpClient` using `fetch_github_token()`.

Add imports:
```python
from erk_shared.gateway.http.auth import fetch_github_token
from erk_shared.gateway.http.real import RealHttpClient
```

Change line 115 from:
```python
http_client=None,
```
to:
```python
http_client=RealHttpClient(token=fetch_github_token(), base_url="https://api.github.com"),
```

### 8. Test file: `tests/unit/services/test_plan_list_service.py`

Replace all 20 occurrences of `http_client=None` with `http_client=FakeHttpClient()`.

Add import at the top of the file:
```python
from erk_shared.gateway.http.fake import FakeHttpClient
```

Lines to change: 54, 98, 117, 160, 201, 268, 321, 349, 390, 435, 617, 631, 661, 700, 724, 768, 807, 850, 889, 922.

### 9. No changes needed (already correct)

These files already use `FakeHttpClient()` or `MagicMock()`:
- `tests/unit/services/test_plan_list_service_http.py` — already passes `FakeHttpClient()`
- `tests/tui/data/test_provider.py` — already passes `FakeHttpClient()`
- `tests/tui/data/test_fetch_objective_content.py` — already passes `FakeHttpClient()`
- `tests/tui/data/test_fetch_plan_content.py` — already passes `FakeHttpClient()`
- `tests/erk_shared/gateway/plan_data_provider/test_real_routing.py` — uses `MagicMock()`
- `src/erk/cli/commands/pr/list_cmd.py` — static mode already uses `FakeHttpClient()`, interactive mode already uses `RealHttpClient`
- `src/erk/cli/commands/exec/scripts/dash_data.py` — already uses `RealHttpClient`

## Files NOT Changing

- `packages/erk-shared/src/erk_shared/core/objective_list_service.py` — The `ObjectiveListService` ABC does not take `http_client` (it's an internal detail of the implementation). No change needed.
- `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — `HttpClient` ABC itself is unchanged.
- `packages/erk-shared/src/erk_shared/gateway/http/fake.py` — `FakeHttpClient` is unchanged.
- `packages/erk-shared/src/erk_shared/gateway/http/real.py` — `RealHttpClient` is unchanged.

## Implementation Order

1. Start with the ABC (`erk_shared/core/plan_list_service.py`) — change signature
2. Update `FakePlanListService` in `erk_shared/core/fakes.py`
3. Update `RealPlanDataProvider` in `erk_shared/gateway/plan_data_provider/real.py`
4. Update `PlannedPRPlanListService` — change signature, remove subprocess fallback, delete `_fetch_workflow_runs_subprocess`
5. Update `RealPlanListService` — change signature
6. Update `RealObjectiveListService` — add `http_client` constructor param, thread through
7. Update `context.py` — thread `http_client` into `RealObjectiveListService`
8. Update `duplicate_check_cmd.py` — create `RealHttpClient`
9. Update test file — replace all `http_client=None` with `FakeHttpClient()`

## Verification

Run:
1. `ty` — type checking should pass with no new errors
2. `ruff check` — linting should pass
3. `pytest tests/unit/services/test_plan_list_service.py` — all existing tests pass
4. `pytest tests/unit/services/test_plan_list_service_http.py` — HTTP path tests pass
5. `pytest tests/tui/data/` — TUI data tests pass
6. `pytest tests/erk_shared/gateway/plan_data_provider/` — routing tests pass
7. `pytest tests/unit/cli/commands/pr/` — CLI command tests pass (if any exist for duplicate-check)