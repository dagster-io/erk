# Plan: Status Line PR Display - Investigation Complete

## Problem Statement

After running `/erk:pr-submit`, the status line showed `(gh:no-pr)` instead of the PR number.

## Investigation Summary

### Timeline from Logs

Analyzed logs from the slot-40 worktree session (`93b993b0-8347-4eff-b3f6-2e66d374582c`):

| Time | Event |
|------|-------|
| 14:39:21 | Status line shows "no PR" (PR doesn't exist yet) |
| 14:39:35 | PR #5715 created on GitHub |
| 14:41:12 | Status line shows PR #5715 correctly |

**Delay: ~2 minutes** between PR creation and status line update.

### Root Cause

The status line WAS working correctly. The "no-pr" display was from **before** the PR was created. The perceived issue was due to:

1. **Stale display timing**: The status line shown to the user was from before PR creation
2. **Graphite cache update delay**: Takes a few seconds after PR creation
3. **Status line refresh timing**: Refreshes on activity, not in real-time

### Session Context Note

Multiple Claude sessions were running:
- **This session** (`2ca3e7de`): In root worktree on master - logs show "no PR" (correct - master has no PR)
- **Slot-40 session** (`93b993b0`): In slot-40 worktree on P5714 branch - correctly shows PR #5715 after ~2 mins

## Conclusion

**No bug exists.** The status line is working correctly:
- It detected the PR within 2 minutes of creation
- The "no-pr" display was from before the PR existed
- After submission, the status line updated correctly

## Implementation Plan: Reduce PR Detection Delay

### Approach

Add polling in `erk pr submit` to wait for the PR to appear in Graphite's cache before the command exits. This ensures the status line can immediately display the PR number.

### Implementation

**File:** `src/erk/cli/commands/submit.py`

Add a helper function to poll for PR in cache:

```python
def _wait_for_pr_in_cache(
    ctx: ErkContext,
    branch: str,
    *,
    max_wait_seconds: float = 10.0,
    poll_interval: float = 0.5,
) -> bool:
    """Wait for PR to appear in Graphite cache after submission.

    Args:
        ctx: Erk context
        branch: Branch name to check
        max_wait_seconds: Maximum time to wait
        poll_interval: Time between checks

    Returns:
        True if PR found in cache, False if timeout
    """
    start = ctx.time.now()
    while (ctx.time.now() - start).total_seconds() < max_wait_seconds:
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, ctx.repo_root)
        if branch in prs:
            return True
        ctx.time.sleep(poll_interval)
    return False
```

Call this after successful `gt submit` in the submit workflow.

### Files to Modify

1. `src/erk/cli/commands/submit.py` - Add `_wait_for_pr_in_cache()` function and call after submission
2. `tests/commands/submit/` - Add tests for the polling behavior

### Testing

1. Unit test: Mock `graphite.get_prs_from_graphite()` to return empty dict initially, then return PR after N calls
2. Integration test: Submit a PR and verify it appears in status line within seconds

### Verification Steps

1. Create a test branch with changes
2. Run `erk pr submit`
3. Immediately check status line - should show PR number
4. Verify logs show polling behavior