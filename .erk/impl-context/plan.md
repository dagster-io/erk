# Fix: Stale branch checkout in plan-implement workflow

## Context

In the one-shot workflow, the plan job pushes commits to the branch (via Claude's `/erk:plan-save`). The implement job then starts on a fresh runner, but `actions/checkout@v4` checks out the `github.sha` resolved at **workflow dispatch time** — before the plan job ran. This means the local branch already exists at the stale SHA. The subsequent `git fetch origin "$BRANCH_NAME"` updates `origin/$BRANCH_NAME` but `git checkout "$BRANCH_NAME"` is a no-op since the local branch already exists. The local branch remains behind the remote, causing `git push` on line 178 to fail with non-fast-forward.

## Fix

**File:** `.github/workflows/plan-implement.yml` (lines 157-158)

Add `git reset --hard "origin/$BRANCH_NAME"` after the fetch+checkout to sync the local branch to the remote tip:

```yaml
git fetch origin "$BRANCH_NAME"
git checkout "$BRANCH_NAME"
# Reset to remote tip — the plan job may have pushed commits after
# actions/checkout resolved github.sha at workflow dispatch time
git reset --hard "origin/$BRANCH_NAME"
```

This is safe because:
- The implement job has no local work to lose at this point
- We want exactly what's on the remote (including the plan job's commits)
- It's idempotent — if already at the tip, it's a no-op

## Verification

1. Re-run the failed workflow run to confirm it passes the "Checkout implementation branch" step
2. Verify a standalone `plan-implement.yml` dispatch still works (the reset is harmless when no plan job preceded it)
