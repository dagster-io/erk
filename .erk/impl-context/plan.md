# Remove PR Cache Polling from Submit Critical Path

## Context

After `erk pr submit` completes, the submit command currently blocks for up to 10 seconds polling `.git/.graphite_pr_info` (a local file) waiting for Graphite to update it. This was added so the status line could immediately show PR info — but it belongs in the status line, not in the submit path. The submit command should complete as fast as possible.

## Files to Modify

- `src/erk/cli/commands/pr/submit_cmd.py` — remove `_wait_for_pr_in_cache`, `ENABLE_PR_CACHE_POLLING`, `PR_CACHE_POLL_MAX_WAIT_SECONDS`, `PR_CACHE_POLL_INTERVAL_SECONDS`, and the polling call after `run_submit_pipeline`
- `src/erk/cli/commands/exec/scripts/push_and_create_pr.py` — remove `_wait_for_pr_in_cache` function and its call at line 83
- `tests/commands/pr/test_submit_pr_cache_polling.py` — delete this file entirely (tests for the removed behavior)

## Changes

### `submit_cmd.py`
- Remove the 4 module-level constants (`ENABLE_PR_CACHE_POLLING`, `PR_CACHE_POLL_MAX_WAIT_SECONDS`, `PR_CACHE_POLL_INTERVAL_SECONDS`)
- Remove the `_wait_for_pr_in_cache` function (lines 38–65)
- Remove the polling block after `run_submit_pipeline` (lines 190–198)
- Remove `user_output` import if no longer used

### `push_and_create_pr.py`
- Remove `_PR_CACHE_POLL_MAX_WAIT_SECONDS`, `_PR_CACHE_POLL_INTERVAL_SECONDS` constants
- Remove `_wait_for_pr_in_cache` function (lines 103–115)
- Remove the call at line 83 (`_wait_for_pr_in_cache(erk_ctx, result.repo_root, result.branch_name)`)

### `tests/commands/pr/test_submit_pr_cache_polling.py`
- Delete the file — it only tests the removed polling behavior

## Verification

```
pytest tests/commands/pr/ -x
```
