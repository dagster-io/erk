# Plan: Replace monkeypatch in doctor tests with HealthCheckRunner gateway

## Context

PR #8847 has a tripwires review comment flagging `monkeypatch.setattr` at `tests/commands/doctor/test_doctor.py:475`. Two test functions (`test_doctor_shows_remediation_for_warnings` at line 383 and `test_doctor_condensed_shows_warning_in_subgroup` at line 444) monkeypatch `run_all_checks` on the doctor module to control CheckResult inputs when testing display logic. Per erk conventions, this should use dependency injection with a gateway fake.

## Approach

Create a `HealthCheckRunner` ABC following the existing service pattern (like `PlanListService`). Add it as an optional field on `ErkContext` (matching the `package_info` / `http_client` pattern for fields only needed by specific commands). The doctor command uses the runner when set; tests inject a fake.

## Implementation Steps

### 1. Create ABC + Real implementation

**New file: `src/erk/core/health_checks/runner.py`**

```python
from abc import ABC, abstractmethod
from erk.core.context import ErkContext
from erk.core.health_checks.models import CheckResult

class HealthCheckRunner(ABC):
    @abstractmethod
    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]: ...

class RealHealthCheckRunner(HealthCheckRunner):
    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
        from erk.core.health_checks import run_all_checks
        return run_all_checks(ctx, check_hooks=check_hooks)
```

### 2. Create Fake implementation

**New file: `tests/fakes/health_check_runner.py`**

```python
from erk.core.health_checks.models import CheckResult
from erk.core.health_checks.runner import HealthCheckRunner

class FakeHealthCheckRunner(HealthCheckRunner):
    def __init__(self, *, results: list[CheckResult]) -> None:
        self._results = results

    def run_all(self, ctx, *, check_hooks: bool) -> list[CheckResult]:
        return self._results
```

### 3. Add field to ErkContext

**Modify: `packages/erk-shared/src/erk_shared/context/context.py`**

- Add TYPE_CHECKING import: `from erk.core.health_checks.runner import HealthCheckRunner`
- Add optional field (with other defaulted fields at bottom): `health_check_runner: HealthCheckRunner | None = None`

### 4. Wire real implementation in production context

**Modify: `src/erk/core/context.py`**

- In `create_context()` (~line 669): add `health_check_runner=RealHealthCheckRunner()` to ErkContext construction

### 5. Update doctor command

**Modify: `src/erk/cli/commands/doctor.py`**

- Line 170: Replace `results = run_all_checks(erk_ctx, check_hooks=check_hooks)` with:
  ```python
  if erk_ctx.health_check_runner is not None:
      results = erk_ctx.health_check_runner.run_all(erk_ctx, check_hooks=check_hooks)
  else:
      results = run_all_checks(erk_ctx, check_hooks=check_hooks)
  ```
- Keep the `from erk.core.health_checks import run_all_checks` import as fallback

### 6. Update test functions

**Modify: `tests/commands/doctor/test_doctor.py`**

- Remove `from erk.cli.commands import doctor as doctor_module` import (line 9) if no other references
- Add import: `from tests.fakes.health_check_runner import FakeHealthCheckRunner`
- **`test_doctor_shows_remediation_for_warnings`** (line 383):
  - Remove `monkeypatch` parameter
  - Create `FakeHealthCheckRunner(results=[...])` with the same CheckResult list
  - Pass `health_check_runner=fake_runner` to `build_workspace_test_context()`
  - Remove `monkeypatch.setattr(...)` block
- **`test_doctor_condensed_shows_warning_in_subgroup`** (line 444):
  - Same changes as above

### Files Summary

| File | Action |
|------|--------|
| `src/erk/core/health_checks/runner.py` | **Create** - ABC + RealHealthCheckRunner |
| `tests/fakes/health_check_runner.py` | **Create** - FakeHealthCheckRunner |
| `packages/erk-shared/src/erk_shared/context/context.py` | **Modify** - Add optional field |
| `src/erk/core/context.py` | **Modify** - Wire real in create_context() |
| `src/erk/cli/commands/doctor.py` | **Modify** - Use runner from context |
| `tests/commands/doctor/test_doctor.py` | **Modify** - Replace monkeypatch with fake |

### Why optional field (not required)

- Only the `doctor` command uses `HealthCheckRunner` — other commands don't need it
- Follows existing pattern: `package_info: ErkPackageInfo | None = None`, `http_client: HttpClient | None = None`
- Avoids updating all 5 ErkContext construction sites (only `create_context()` changes)
- Doctor command has a clean fallback to the direct `run_all_checks()` call

## Verification

1. Run doctor tests: `pytest tests/commands/doctor/test_doctor.py`
2. Verify the two previously-monkeypatched tests pass without `monkeypatch` fixture
3. Run type checker: `ty` on modified files
4. Run linter: `ruff check` on modified files
5. Grep for remaining monkeypatch in test_doctor.py to confirm elimination
