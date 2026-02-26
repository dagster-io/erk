# Fix CI: git add fails for .erk/impl-context due to .gitignore

## Context

PR #8308 added `.erk/impl-context/` to `.gitignore` to prevent accidental local commits. However, the `plan-implement.yml` CI workflow intentionally commits this directory to the branch (temporarily, for reruns) and then removes it before running the agent. The `git add .erk/impl-context` call on line 161 now exits with code 1 because git refuses to add gitignored paths without `-f`.

**Failing job**: https://github.com/dagster-io/erk/actions/runs/22455362975/job/65034965116

**Error message**:
```
The following paths are ignored by one of your .gitignore files:
.erk/impl-context
hint: Use -f if you really want to add them.
Process completed with exit code 1.
```

## Fix

Change `git add .erk/impl-context` to `git add -f .erk/impl-context` in the "Checkout implementation branch" step of `.github/workflows/plan-implement.yml`.

**File**: `.github/workflows/plan-implement.yml`, line 161

**Change**:
```diff
-          git add .erk/impl-context
+          git add -f .erk/impl-context
```

The `-f` (force) flag allows adding gitignored paths intentionally. This is correct here because:
- The workflow explicitly needs to track `impl-context` in the branch for rerun support
- A subsequent step (`Remove plan staging dirs from git tracking`) uses `git rm -rf .erk/impl-context/` to clean it up before the agent runs

## Verification

After the fix, re-trigger the failing CI run and confirm the "Checkout implementation branch" step succeeds.
