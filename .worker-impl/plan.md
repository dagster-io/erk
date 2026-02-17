# Plan: Migrate managed artifacts tests in test_health_checks.py

**Part of Objective #7129, Step 1.5** (completes Phase 1)

## Context

`check_managed_artifacts()` takes only `repo_root: Path` and internally computes its dependencies (`ErkPackageInfo`, `installed_capabilities`), forcing 9 tests to monkeypatch these internal calls. Steps 1.1-1.4 established the parameter injection pattern for the artifacts layer; this step applies the same pattern to the health checks layer.

## Approach

Add `package` and `installed_capabilities` as required keyword-only parameters to `check_managed_artifacts()`, eliminating 12 of 14 monkeypatch calls. The remaining 2 (`get_managed_artifacts` patches in artifact_health.py) are deferred to Phase 2.

## Changes

### 1. Modify `check_managed_artifacts` signature

**File:** `src/erk/core/health_checks.py` (line 1412)

```python
# Before
def check_managed_artifacts(repo_root: Path) -> CheckResult:

# After
def check_managed_artifacts(
    repo_root: Path,
    *,
    package: ErkPackageInfo,
    installed_capabilities: frozenset[str] | None,
) -> CheckResult:
```

Remove the internal computation lines:
- Line 1424: `package = ErkPackageInfo.from_project_dir(repo_root)`
- Lines 1440-1444: the `installed_capabilities` computation block

The rest of the function body stays identical (it already uses `package` and `installed_capabilities` as locals).

### 2. Update the single caller `run_all_checks`

**File:** `src/erk/core/health_checks.py` (line 1535)

Move the dependency computation to the caller:

```python
package = ErkPackageInfo.from_project_dir(repo_root)
managed_capabilities: frozenset[str] | None = None
if not package.in_erk_repo:
    managed_capabilities = load_installed_capabilities(repo_root)
results.append(
    check_managed_artifacts(
        repo_root,
        package=package,
        installed_capabilities=managed_capabilities,
    )
)
```

### 3. Migrate 10 tests

**File:** `tests/core/test_health_checks.py` (lines 523-989)

| Test | Patches removed | Patches remaining |
|------|:-:|:-:|
| `test_check_managed_artifacts_no_claude_dir` (526) | 0 (add new params) | 0 |
| `test_check_managed_artifacts_in_erk_repo` (536) | 1 | 0 |
| `test_check_managed_artifacts_produces_type_summary` (571) | 1 | 0 |
| `test_check_managed_artifacts_some_not_installed` (607) | 1 | 0 |
| `test_check_managed_artifacts_shows_type_summary` (646) | 2 | 0 |
| `test_check_managed_artifacts_actions_optional_without_workflows` (693) | 2 | 1 (`get_managed_artifacts`) |
| `test_check_managed_artifacts_actions_required_with_workflows` (750) | 2 | 1 (`get_managed_artifacts`) |
| `test_check_managed_artifacts_changed_upstream_remediation` (819) | 1 | 0 |
| `test_check_managed_artifacts_locally_modified_remediation` (875) | 1 | 0 |
| `test_check_managed_artifacts_verbose_status_explanations` (958) | 1 | 0 |

**Pattern for each test:**
- Remove `monkeypatch: pytest.MonkeyPatch` from signature (unless test still needs it for `get_managed_artifacts`)
- Remove `monkeypatch.setattr(ErkPackageInfo, "from_project_dir", ...)` line
- Remove `monkeypatch.setattr("erk.core.health_checks.load_installed_capabilities", ...)` line (3 tests)
- Pass `package=package` and `installed_capabilities=...` directly to `check_managed_artifacts()`

**Example (typical test):**
```python
# Before
def test_...(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = ErkPackageInfo.test_package(bundled_claude_dir=bundled_dir)
    monkeypatch.setattr(ErkPackageInfo, "from_project_dir", staticmethod(lambda _: package))
    result = check_managed_artifacts(tmp_path)

# After
def test_...(tmp_path: Path) -> None:
    package = ErkPackageInfo.test_package(bundled_claude_dir=bundled_dir)
    result = check_managed_artifacts(tmp_path, package=package, installed_capabilities=None)
```

**For `test_check_managed_artifacts_no_claude_dir`** (currently no monkeypatch): Add a minimal `ErkPackageInfo.test_package(bundled_claude_dir=tmp_path / "bundled" / ".claude")` and pass `installed_capabilities=None`. The test hits the early return before these are used.

## Result

**14 monkeypatch calls reduced to 2.** The 2 remaining (`get_managed_artifacts`) patch a cached function deep in `artifact_health.py` -- a different scope better suited to Phase 2.

## Verification

1. `pytest tests/core/test_health_checks.py -k "managed_artifacts" -v`
2. `pytest tests/core/test_health_checks.py -v` (full file)
3. `ty check src/erk/core/health_checks.py`
4. Grep for remaining monkeypatch in managed artifacts section (expect 2)