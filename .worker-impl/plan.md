# Plan: Make .worker-impl/ Cleanup Conditional in GitHub Actions Workflow

## Goal

Fix the GitHub Actions workflow to gracefully handle cases where `.worker-impl/` doesn't exist during the cleanup phase, preventing workflow failures when the folder is missing.

## Problem

The `dispatch-erk-queue-git.yml` workflow unconditionally tries to remove `.worker-impl/` after implementation succeeds:

```bash
git rm -rf .worker-impl/
git commit -m "Remove .worker-impl/ folder after implementation"
git push origin "$BRANCH_NAME"
```

When `.worker-impl/` doesn't exist (for any reason), `git rm` fails with:
```
fatal: pathspec '.worker-impl/' did not match any files
Error: Process completed with exit code 128.
```

This causes the entire workflow to fail even though the implementation succeeded.

## Root Cause

While `.worker-impl/` **should** always exist if the workflow reaches this phase (created in Phase 2 by `dot-agent run erk create-worker-impl-from-issue`), defensive programming requires handling the edge case where it might be missing due to:
- Workflow logic changes
- Race conditions
- Manual intervention
- Bugs in earlier phases

## Solution

Make the cleanup step conditional - only attempt to remove `.worker-impl/` if it actually exists.

## Implementation Steps

### 1. Locate the Cleanup Step

**File:** `.github/workflows/dispatch-erk-queue-git.yml`

Find the cleanup step that runs after successful implementation. Based on the workflow structure, this is in Phase 5 (Submission and Cleanup) after the implementation succeeds.

### 2. Add Conditional Check

Replace the unconditional cleanup:

```yaml
# Current (unconditional)
- name: Clean up .worker-impl folder
  run: |
    git rm -rf .worker-impl/
    git commit -m "Remove .worker-impl/ folder after implementation"
    git push origin "$BRANCH_NAME"
```

With a defensive version that checks if the folder exists first:

```yaml
# Defensive (conditional)
- name: Clean up .worker-impl folder
  run: |
    if [ -d .worker-impl/ ]; then
      git rm -rf .worker-impl/
      git commit -m "Remove .worker-impl/ folder after implementation"
      git push origin "$BRANCH_NAME"
      echo "✓ .worker-impl/ folder removed"
    else
      echo "⚠ .worker-impl/ folder not found - skipping cleanup"
    fi
```

### 3. Alternative: Use || true for Resilience

If we want even more resilience, we can use `|| true` to continue even if `git rm` fails:

```yaml
- name: Clean up .worker-impl folder
  run: |
    if [ -d .worker-impl/ ]; then
      git rm -rf .worker-impl/ || true
      if [ -z "$(git status --porcelain)" ]; then
        echo "⚠ No changes to commit (folder already removed)"
      else
        git commit -m "Remove .worker-impl/ folder after implementation"
        git push origin "$BRANCH_NAME"
        echo "✓ .worker-impl/ folder removed"
      fi
    else
      echo "⚠ .worker-impl/ folder not found - skipping cleanup"
    fi
```

**Recommendation:** Use the simpler conditional check (option in step 2) unless we need the extra resilience.

## Testing

After implementation, test by:

1. **Normal case:** Run a workflow where `.worker-impl/` exists - verify it gets cleaned up
2. **Missing folder case:** Manually delete `.worker-impl/` before cleanup step - verify workflow continues without error
3. **Already cleaned case:** Run cleanup twice - verify second run handles gracefully

## Critical Files

- `.github/workflows/dispatch-erk-queue-git.yml` - Add conditional check to cleanup step

## Notes

- This is a defensive fix that handles the symptom (missing folder) rather than the root cause
- If `.worker-impl/` is consistently missing, we should investigate **why** the folder creation in Phase 2 is failing
- The warning message will help diagnose if this becomes a recurring issue