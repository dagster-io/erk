# Fix Doctor Warning Display & Add Artifact Allowlist

## Context

`erk doctor` has two issues:
1. **Warning/remediation mismatch**: In non-verbose mode, warnings (like locally-modified artifacts) are hidden behind green checkmarks in condensed subgroups. The Remediation section shows a fix, but the final summary says "All checks passed!" — contradictory and easy to miss.
2. **No way to allow local modifications**: Users who intentionally modify managed artifacts (e.g., customizing a GitHub Action) get persistent warnings with no suppression mechanism.

## Issue 1: Fix Doctor Warning Display

### Files to modify
- `src/erk/cli/commands/doctor.py`
- `tests/commands/doctor/test_doctor.py`

### Changes

**`_format_subgroup()` (doctor.py:86-105)** — Make condensed mode warning-aware:

After computing `all_passed` on line 88, add:
```python
has_warnings = any(c.warning for c in checks)
```

Replace the condensed branch (lines 95-105) with three cases:
- `all_passed and not has_warnings` → green checkmark, condensed (existing behavior)
- `all_passed and has_warnings` → yellow ⚠️ icon, expand warning checks (new)
- `not all_passed` → red ❌, expand failures (existing behavior)

The warning expansion mirrors the failure expansion pattern at lines 103-105.

**Final summary (doctor.py:254-261)** — Acknowledge warnings:

Add `has_warnings = any(r.warning for r in checks_for_summary)` and add a middle case:
- `failed == 0 and not has_warnings` → "✨ All checks passed!"
- `failed == 0 and has_warnings` → "⚠️ Checks passed with warnings"
- `failed > 0` → "⚠️ N check(s) failed"

### Tests

- Update `test_doctor_shows_remediation_for_warnings` to also assert the final summary says "Checks passed with warnings" (not "All checks passed!")
- Add `test_doctor_condensed_shows_warning_in_subgroup`: mock `run_all_checks` returning a check in the "Erk configuration" subgroup with `passed=True, warning=True`, assert the output contains "⚠️" for the subgroup and expands the warning check

## Issue 2: Artifact Allowlist

### Config format

```toml
# .erk/config.toml (committed) or .erk/config.local.toml (gitignored)
[artifacts]
allow_modified = [
    "actions/setup-claude-erk",
]
```

Keys use the same format as `.erk/state.toml` artifact keys (e.g., `actions/setup-claude-erk`, `skills/dignified-python`, `commands/erk/plan-save.md`).

### Files to modify
- `src/erk/core/health_checks/managed_artifacts.py`
- `tests/artifacts/test_artifact_health.py`

### Changes

**`managed_artifacts.py`** — Add `_load_artifact_allowlist()` and filter in `_build_managed_artifacts_result()`:

1. New function `_load_artifact_allowlist(repo_root: Path) -> frozenset[str]`:
   - Reads `[artifacts].allow_modified` from both `.erk/config.toml` and `.erk/config.local.toml`
   - Returns union of both lists as `frozenset[str]`
   - Uses `tomllib` (already available in Python 3.11+)
   - Returns empty frozenset if no config files or no `[artifacts]` section

2. Modify `_build_managed_artifacts_result(result, *, allow_modified)`:
   - Add `allow_modified: frozenset[str]` parameter
   - Before building `by_type` grouping, post-process artifacts: if status is `"locally-modified"` and `artifact.name` is in `allow_modified`, override effective status to `"up-to-date"`
   - In verbose output, annotate allowed artifacts with `"(locally-modified, allowed by config)"`

3. Update `check_managed_artifacts()`:
   - Call `_load_artifact_allowlist(repo_root)` and pass to `_build_managed_artifacts_result()`

### Tests

- `test_load_artifact_allowlist_empty_when_no_config`: Returns empty frozenset when no config
- `test_load_artifact_allowlist_reads_config_toml`: Reads from `.erk/config.toml`
- `test_load_artifact_allowlist_merges_both_configs`: Union of `config.toml` + `config.local.toml`
- `test_build_managed_artifacts_result_allows_locally_modified`: Allowed artifact → no warning, no remediation
- `test_build_managed_artifacts_result_verbose_shows_allowed_annotation`: Verbose shows "(locally-modified, allowed by config)"

## Implementation Order

1. Fix `_format_subgroup()` warning display
2. Fix final summary warning display
3. Add tests for Issue 1
4. Add `_load_artifact_allowlist()`
5. Modify `_build_managed_artifacts_result()` for allowlist filtering
6. Wire up in `check_managed_artifacts()`
7. Add tests for Issue 2

## Verification

1. Run `pytest tests/commands/doctor/test_doctor.py` — all existing + new tests pass
2. Run `pytest tests/artifacts/test_artifact_health.py` — all existing + new tests pass
3. Run `ruff check` and `ty check` on modified files
4. Manual test in a repo with locally-modified artifacts: `erk doctor` should show ⚠️ in condensed mode and "Checks passed with warnings" in summary
5. Manual test with allowlist configured: `erk doctor` should suppress warning for allowed artifacts
