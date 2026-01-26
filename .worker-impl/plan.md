# Plan: Add CIRunner Gateway to Eliminate subprocess.run Mocks

## Summary

Create a `CIRunner` gateway abstraction to replace `monkeypatch.setattr("subprocess.run", ...)` in `test_ci_verify_autofix.py`, following the fake-driven-testing pattern.

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/gateway/ci_runner/__init__.py`

Empty init file for package.

### 2. `packages/erk-shared/src/erk_shared/gateway/ci_runner/abc.py`

- `CICheckResult` frozen dataclass with `passed: bool` and `error_type: str | None`
- `CIRunner` ABC with single method:
  ```python
  @abstractmethod
  def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult: ...
  ```

### 3. `packages/erk-shared/src/erk_shared/gateway/ci_runner/real.py`

- `RealCIRunner` implementation using `subprocess.run(cmd, cwd=cwd, check=True, capture_output=False)`
- Handles `CalledProcessError` → `CICheckResult(passed=False, error_type="command_failed")`
- Handles `FileNotFoundError` → `CICheckResult(passed=False, error_type="command_not_found")`

### 4. `packages/erk-shared/src/erk_shared/gateway/ci_runner/fake.py`

- `FakeCIRunner` with constructor params:
  - `failing_checks: set[str] | None` - check names that should fail
  - `missing_commands: set[str] | None` - check names with missing command
- Properties for assertions: `run_calls`, `check_names_run`

## Files to Modify

### 5. `src/erk/cli/commands/exec/scripts/ci_verify_autofix.py`

**Add import:**

```python
from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner
from erk_shared.gateway.ci_runner.real import RealCIRunner
```

**Update `_run_check()`:** Add `ci_runner: CIRunner` parameter, replace subprocess.run with:

```python
result = ci_runner.run_check(name=name, cmd=cmd, cwd=cwd)
if not result.passed:
    if result.error_type == "command_not_found":
        click.echo(f"::error::{name} command not found", err=True)
    else:
        click.echo(f"::error::{name} check failed", err=True)
return result.passed
```

**Update `_verify_autofix_impl()`:** Add `ci_runner: CIRunner` parameter, pass to `_run_check()`.

**Update `ci_verify_autofix` Click command:** Create `RealCIRunner()` and pass to `_verify_autofix_impl()`.

### 6. `tests/unit/cli/commands/exec/scripts/test_ci_verify_autofix.py`

**Remove:** All `monkeypatch` usage and inline `MockResult` classes.

**Add import:**

```python
from erk_shared.gateway.ci_runner.fake import FakeCIRunner
```

**Update tests:** Pass `ci_runner=FakeCIRunner(...)` to `_verify_autofix_impl()`. Configure failures via:

```python
ci_runner = FakeCIRunner(failing_checks={"lint"})
```

## Files to Add (Tests)

### 7. `tests/unit/fakes/test_fake_ci_runner.py`

Unit tests for FakeCIRunner:

- Test default behavior (all pass)
- Test `failing_checks` configuration
- Test `missing_commands` configuration
- Test `run_calls` tracking

## Design Notes

- **3-file pattern** (no dry_run/printing): CI checks are observational, not destructive
- **Not added to ErkContext**: Scoped to this exec command only
- **Pattern follows**: `gateway/time/` as template

## Verification

1. Run `make test` scoped to the test file:

   ```
   uv run pytest tests/unit/cli/commands/exec/scripts/test_ci_verify_autofix.py -v
   ```

2. Run `make ty` to verify type checking passes

3. Verify no `monkeypatch` or `mock` imports remain in the test file
