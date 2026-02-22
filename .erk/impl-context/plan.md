# Plan: Add `.worker-impl/` cleanup to `pr-address` workflow

## Context

`.worker-impl/` folders are leaking into PRs. In PR #7795, the `plan-implement` workflow correctly cleaned up `.worker-impl/`, but a local re-submission (`erk submit`) re-created it at 09:28Z. The `pr-address` workflow then ran at 09:31Z, addressed review comments, and pushed — but it has **no `.worker-impl/` cleanup logic**, so the folder persisted in the PR.

The multi-layer cleanup architecture documented in `docs/learned/planning/worktree-cleanup.md` only covers the `plan-implement` workflow. The `pr-address` workflow is a blind spot.

## Root Cause

The `pr-address.yml` workflow (`.github/workflows/pr-address.yml`) doesn't check for or remove `.worker-impl/` or `.erk/impl-context/` before pushing. When these folders exist on the branch (from re-submissions, failed cleanups, or any other source), `pr-address` propagates them.

## Fix

Add a cleanup step to `.github/workflows/pr-address.yml` after Claude addresses comments but before the final push (line 72-80).

### File: `.github/workflows/pr-address.yml`

Insert a new step between "Address PR review comments" and "Push changes":

```yaml
    - name: Clean up plan staging dirs if present
      run: |
        NEEDS_CLEANUP=false
        if [ -d .worker-impl/ ] && git ls-files --error-unmatch .worker-impl/ >/dev/null 2>&1; then
          git rm -rf .worker-impl/
          NEEDS_CLEANUP=true
        fi
        if [ -d .erk/impl-context/ ] && git ls-files --error-unmatch .erk/impl-context/ >/dev/null 2>&1; then
          git rm -rf .erk/impl-context/
          NEEDS_CLEANUP=true
        fi
        if [ "$NEEDS_CLEANUP" = true ]; then
          git commit -m "Remove plan staging dirs"
          echo "Cleaned up plan staging dirs"
        fi
```

This is idempotent — if the folders don't exist or aren't tracked, it does nothing.

### File: `docs/learned/planning/worktree-cleanup.md`

Update the multi-layer cleanup documentation to note that `pr-address` now also has cleanup logic.

## Verification

1. Check that the step is correctly placed between "Address PR review comments" and "Push changes"
2. Verify the `git ls-files --error-unmatch` guard prevents errors when `.worker-impl/` doesn't exist
3. Run fast-ci to ensure no test impacts
