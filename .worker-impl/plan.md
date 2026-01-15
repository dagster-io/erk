# Plan: Add Concurrency Setting to CI Workflow

## Problem

When pushing to a branch with an open PR, both `push` and `pull_request` events trigger separate CI runs. This causes:
- Redundant resource usage (two full CI runs for the same commit)
- Confusing PR check status (shows "pending" even when push-triggered CI passed)
- Wasted GitHub Actions minutes

## Solution

Add a `concurrency` block to `.github/workflows/ci.yml` that:
1. Groups runs by branch name
2. Cancels in-progress runs when a new commit is pushed

## Implementation

**File:** `.github/workflows/ci.yml`

Add after `permissions:` block (around line 12):

```yaml
concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

**How it works:**
- `github.head_ref` is the PR source branch (set for `pull_request` events)
- `github.ref` is the branch ref (set for `push` events)
- Using `||` ensures both event types use the same group key for the same branch
- `cancel-in-progress: true` cancels any queued/running workflow when a new one starts

## Verification

1. Push a commit to a branch with an open PR
2. Verify only one CI run executes (not two)
3. Push another commit while CI is running
4. Verify the first run is cancelled and only the new run continues