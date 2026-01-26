# Fix: PR Summary Including .worker-impl/ Files

## Problem

PR #6090 summary incorrectly lists `.worker-impl/` files (README.md, issue.json, plan.md) as part of the implementation changes.

**Root Cause**: In `.github/workflows/erk-impl.yml`, the "Update PR body with implementation summary" step (line 323) runs BEFORE the "Clean up .worker-impl/" step (line 336). When the PR summary is generated via `gh pr diff`, the `.worker-impl/` files are still on the remote branch.

## Solution

Move the `.worker-impl/` cleanup step to run BEFORE the PR body update step.

### Current Order (incorrect):
1. Submit branch (line 279) - pushes with `.worker-impl/`
2. Mark PR ready (line 314)
3. **Update PR body with summary (line 323)** - fetches diff that includes `.worker-impl/`
4. Clean up `.worker-impl/` (line 336) - too late

### New Order (correct):
1. Submit branch (line 279) - pushes with `.worker-impl/`
2. Mark PR ready (line 314)
3. **Clean up `.worker-impl/` (moved here)** - removes artifacts from remote
4. **Update PR body with summary** - fetches clean diff

## Implementation

**File**: `.github/workflows/erk-impl.yml`

Move lines 336-351 (the "Clean up .worker-impl/ after implementation" step) to appear before lines 323-334 (the "Update PR body with implementation summary" step).

The cleanup step already has the same `if` condition as the PR body update step, so no condition changes are needed.

## Verification

1. Submit a test plan for remote implementation
2. Check that the resulting PR summary does NOT include `.worker-impl/` files
3. Verify the PR diff on GitHub shows only the actual implementation changes