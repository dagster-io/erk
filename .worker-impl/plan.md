# Plan: Update upgrade instructions from `uv tool upgrade` to project-based upgrade

## Summary

Replace outdated `uv tool upgrade erk` copy with the project-based upgrade command since erk is now installed as a project dependency rather than a global tool.

## Files to Modify

### 1. `src/erk/core/health_checks.py:129`
Change remediation from:
```python
remediation="Run 'uv tool upgrade erk' to update",
```
To:
```python
remediation="Run 'uv sync --upgrade-package erk' to update",
```

### 2. `src/erk/core/version_check.py:54`
Change from:
```python
f"   Update: uv tool upgrade erk"
```
To:
```python
f"   Update: uv sync --upgrade-package erk"
```

### 3. `tests/unit/core/test_version_check.py:71`
Update test assertion from:
```python
assert "uv tool upgrade erk" in result
```
To:
```python
assert "uv sync --upgrade-package erk" in result
```

### 4. `dev/install-test/README.md:10`
Update documentation to reflect project-based upgrade.

## Files NOT Modified

- `CHANGELOG.md:516` - Historical changelog entry, should remain as-is to document what was true at the time

## Verification

Run the test to ensure it passes:
```bash
pytest tests/unit/core/test_version_check.py -v
```