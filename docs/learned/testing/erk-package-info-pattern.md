---
title: ErkPackageInfo Value Object
read_when:
  - "working with ErkPackageInfo or bundled paths"
  - "understanding is_in_erk_repo detection"
  - "writing tests that need ErkPackageInfo"
tripwires:
  - action: "creating ErkPackageInfo directly in production code"
    warning: "Use ErkPackageInfo.from_project_dir(). Direct construction is for tests only."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# ErkPackageInfo Value Object

`ErkPackageInfo` consolidates package-level metadata into a single frozen dataclass, providing two construction paths: one for production and one for tests.

## Class Definition

<!-- Source: src/erk/artifacts/paths.py, ErkPackageInfo -->

See `ErkPackageInfo` in `src/erk/artifacts/paths.py`. Frozen dataclass with fields: `in_erk_repo`, `bundled_claude_dir`, `bundled_github_dir`, `bundled_erk_dir`, `current_version`.

## Two-Constructor Pattern

### Production: from_project_dir()

<!-- Source: src/erk/artifacts/paths.py, ErkPackageInfo.from_project_dir -->

See `ErkPackageInfo.from_project_dir()` in `src/erk/artifacts/paths.py`. Calls `is_in_erk_repo()`, `get_bundled_claude_dir()`, `get_bundled_github_dir()`, `get_bundled_erk_dir()`, and `get_current_version()` to fully populate all fields. Uses inline imports to avoid circular dependencies.

### Tests: test_package()

<!-- Source: src/erk/artifacts/paths.py, ErkPackageInfo.test_package -->

See `ErkPackageInfo.test_package()` in `src/erk/artifacts/paths.py`. Static factory that requires `bundled_claude_dir` and auto-derives `bundled_github_dir` and `bundled_erk_dir` from `bundled_claude_dir.parent` if not provided (assumes `.claude`, `.github`, `.erk` sibling layout). Used across 20+ test files for parameter injection.

## is_in_erk_repo Detection

<!-- Source: src/erk/artifacts/detection.py, is_in_erk_repo -->

See `is_in_erk_repo()` in `src/erk/artifacts/detection.py`. Checks for `pyproject.toml` containing `name = "erk"` to distinguish between editable installs (source repo) and wheel installs (site-packages). When `True`, all bundled artifacts are read from source paths rather than installed paths.

## None Sentinel in installed_capabilities

The `check_managed_artifacts()` function (in `src/erk/core/health_checks.py`) uses `installed_capabilities: frozenset[str] | None` with sentinel semantics:

| Value            | Meaning                          | Context                                                                        |
| ---------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| `None`           | Skip capability filtering        | Running in erk repo (`in_erk_repo=True`) - all artifacts available from source |
| `frozenset[str]` | Filter by installed capabilities | External repo - only check artifacts for installed capabilities                |

<!-- Source: src/erk/core/health_checks.py, check_managed_artifacts -->

See `check_managed_artifacts()` in `src/erk/core/health_checks.py` for the sentinel pattern — `None` when `in_erk_repo` is `True`, otherwise `load_installed_capabilities(repo_root)`.

## Related Topics

- [Parameter Injection Pattern](parameter-injection-pattern.md) - How ErkPackageInfo fits the broader injection pattern
- [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) - Migration from monkeypatch to injectable constructors
