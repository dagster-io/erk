# Plan: Fix erk doctor to explain and remediate changed-upstream artifacts

## Problem

When `erk doctor --verbose` shows hooks with "changed-upstream" status, it:
1. Doesn't explain what "changed-upstream" means
2. Doesn't tell the user how to fix it

```
⚠️ hooks (2) - 2 changed upstream
   exit-plan-mode-hook (changed-upstream)
   user-prompt-hook (changed-upstream)
```

This is unhelpful. Users need to understand:
- **What it means**: The erk package has newer versions of these artifacts
- **How to fix it**: Run `erk artifact sync`

## Root Cause

In `src/erk/core/health_checks.py`:

1. **Line 1369-1371**: Remediation message only set for `"not-installed"`:
   ```python
   if overall_worst == "not-installed":
       remediation = "Run 'erk artifact sync' to restore missing artifacts"
   ```

2. **Line 1362**: Verbose output just appends the raw status without explanation:
   ```python
   status_indicator = f" ({artifact_info.status})"
   ```

## Solution

### Change 1: Add remediation for all issue types (lines ~1368-1371)

```python
remediation: str | None = None
if overall_worst == "not-installed":
    remediation = "Run 'erk artifact sync' to restore missing artifacts"
elif overall_worst == "changed-upstream":
    remediation = "Run 'erk artifact sync' to update to latest erk version"
elif overall_worst == "locally-modified":
    remediation = "Run 'erk artifact sync --force' to restore erk defaults"
```

### Change 2: Add explanatory notes in verbose details (after line ~1363)

After the artifact list, add status explanations when issues exist:

```python
# Add status explanations in verbose output
status_explanations: list[str] = []
if "changed-upstream" in [a.status for artifacts_list in by_type.values() for a in artifacts_list]:
    status_explanations.append("   (changed-upstream): erk has newer versions of these artifacts")
if "locally-modified" in [a.status for artifacts_list in by_type.values() for a in artifacts_list]:
    status_explanations.append("   (locally-modified): these artifacts were edited locally")
if "not-installed" in [a.status for artifacts_list in by_type.values() for a in artifacts_list]:
    status_explanations.append("   (not-installed): these artifacts are missing from the project")

if status_explanations:
    verbose_summaries.append("")  # blank line
    verbose_summaries.extend(status_explanations)
```

## Expected Output (after fix)

```
⚠️ hooks (2) - 2 changed upstream
   exit-plan-mode-hook (changed-upstream)
   user-prompt-hook (changed-upstream)

   (changed-upstream): erk has newer versions of these artifacts

Run 'erk artifact sync' to update to latest erk version
```

## Files to Modify

- `src/erk/core/health_checks.py` (function `_build_managed_artifacts_result`, lines ~1368-1371 and ~1363)

## Verification

1. Run `erk doctor --verbose` in dagster-compass (which has changed-upstream hooks)
2. Verify output shows explanation and remediation
3. Run tests via devrun agent: `pytest tests/artifacts/test_artifact_health.py -v`

## Test Coverage

Existing test file `tests/artifacts/test_artifact_health.py` covers artifact status determination. The changes are additive (adding remediation messages that were previously `None`), so existing tests should pass without modification.