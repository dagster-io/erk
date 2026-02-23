# Add exponential backoff to workflow run polling

## Context

The `trigger_workflow()` method in `RealGitHub` polls for a newly-triggered GitHub Actions workflow run by matching a correlation ID in the run's `displayTitle`. Currently it uses 15 attempts with fixed delays (1s for first 5, 2s for remaining 10), totaling ~25 seconds. This isn't enough time for GitHub API eventual consistency in some cases — the `erk learn` command fails after exhausting all 15 attempts.

The fix: switch to exponential backoff with 7 total attempts, covering more total wait time with fewer requests.

## Changes

### File: `packages/erk-shared/src/erk_shared/gateway/github/real.py` (lines 339-398)

Replace the current polling strategy:

```python
# Current: 15 attempts, fixed 1s/2s delays (~25s total)
max_attempts = 15
...
delay = 1 if attempt < 5 else 2
```

With exponential backoff over 7 attempts:

```python
max_attempts = 7
# Exponential backoff: 1, 2, 4, 8, 8, 8 seconds between attempts
# Total max wait: ~31 seconds
...
delay = min(2 ** attempt, 8)
```

The schedule:
- Attempt 1: immediate
- Attempt 2: 1s delay
- Attempt 3: 2s delay
- Attempt 4: 4s delay
- Attempt 5: 8s delay (capped)
- Attempt 6: 8s delay (capped)
- Attempt 7: 8s delay (capped)

Update the comment on line 338 from "fast path (5×1s) then slow path (10×2s)" to describe the exponential backoff strategy.

## Verification

1. Run existing test: `pytest tests/unit/core/github/test_trigger_workflow.py`
2. Run ty/ruff checks on the modified file
3. The existing tests use `FakeGitHub` which doesn't exercise the polling loop, so no test changes needed
