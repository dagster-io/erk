# Plan: Add User-Visible Progress Output to Polling Loops

## Context

When `erk plan submit` triggers a GitHub Actions workflow, the `trigger_workflow` method polls up to 15 times (~25 seconds) to find the run ID. During this time, the user sees nothing after "Triggering workflow: plan-implement.yml" until either success or a 30-second timeout. Other polling loops have the same problem. The fix: print a status line on every poll attempt so the user knows something is happening.

## Polling Loops to Update

### 1. Workflow Run ID Polling (the one that triggered this)
- **File**: `packages/erk-shared/src/erk_shared/gateway/github/real.py:341-397`
- **Current**: Only `debug_log()` (invisible without `ERK_DEBUG=1`)
- **Change**: Add `user_output()` on each poll attempt
- **Message**: `"  Waiting for workflow run... (attempt {attempt + 1}/{max_attempts})"`

### 2. PR Cache Polling (Graphite)
- **File**: `src/erk/cli/commands/pr/submit_cmd.py:55-61`
- **Current**: Completely silent
- **Change**: Add `user_output()` on each poll iteration
- **Message**: `"  Waiting for PR in Graphite cache..."`  (only on first iteration to avoid spam given 0.5s interval — or a dot-based approach)
- **Approach**: Print a single message before the loop starts, since 0.5s intervals would spam. Add a final timeout message if it fails.

### 3. Auto-Close Issue Polling
- **File**: `src/erk/cli/commands/objective_helpers.py:48-66`
- **Current**: Only `logger.debug()` (invisible at normal log levels)
- **Change**: Add `user_output()` on each retry
- **Message**: `"  Waiting for issue #{issue_number} to close... (attempt {attempt + 1}/{max_retries})"`

### 4. Git Index Lock Waiting
- **File**: `packages/erk-shared/src/erk_shared/gateway/git/lock.py:84-86`
- **Current**: Completely silent
- **Change**: Add `user_output()` on first detection and periodically
- **Message**: `"  Waiting for git index.lock to be released..."` (once on entry, since 0.5s intervals)

### 5. Generic Retry (`with_retries`)
- **File**: `packages/erk-shared/src/erk_shared/gateway/github/retry.py:114-136`
- **Current**: Prints to `sys.stderr` on retries — already has progress output
- **No change needed** — already prints on each retry

## Detailed Changes

### `real.py` — `trigger_workflow` polling loop (line ~341)

Add a `user_output` call at the top of each polling iteration:

```python
for attempt in range(max_attempts):
    user_output(f"  Waiting for workflow run... (attempt {attempt + 1}/{max_attempts})")
    debug_log(f"trigger_workflow: polling attempt {attempt + 1}/{max_attempts}")
```

### `submit_cmd.py` — `_wait_for_pr_in_cache` (line ~55)

Add a single message before the loop and a counter for periodic updates:

```python
def _wait_for_pr_in_cache(...) -> bool:
    start = ctx.time.now()
    user_output("  Waiting for PR to appear in Graphite cache...")
    while (ctx.time.now() - start).total_seconds() < max_wait_seconds:
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo_root)
        if branch in prs:
            return True
        ctx.time.sleep(poll_interval)
    return False
```

### `objective_helpers.py` — `_wait_for_issue_closure` (line ~48)

Replace `logger.debug` with `user_output` for the retry messages:

```python
for attempt in range(_AUTO_CLOSE_MAX_RETRIES):
    user_output(f"  Waiting for issue #{issue_number} to close... (attempt {attempt + 1}/{_AUTO_CLOSE_MAX_RETRIES})")
    ctx.time.sleep(_AUTO_CLOSE_RETRY_DELAY)
```

### `lock.py` — `wait_for_index_lock` (line ~84)

Add a one-time message when lock is detected:

```python
printed = False
while lock_path.exists() and elapsed < max_wait_seconds:
    if not printed:
        user_output("  Waiting for git index.lock to be released...")
        printed = True
    time.sleep(poll_interval)
    elapsed += poll_interval
```

Note: `lock.py` is in `erk_shared` gateway layer and currently doesn't import `user_output`. Need to add the import.

## Files Modified

1. `packages/erk-shared/src/erk_shared/gateway/github/real.py` — add `user_output` in polling loop
2. `src/erk/cli/commands/pr/submit_cmd.py` — add `user_output` before polling loop
3. `src/erk/cli/commands/objective_helpers.py` — replace `logger.debug` with `user_output` in retry loop
4. `packages/erk-shared/src/erk_shared/gateway/git/lock.py` — add `user_output` on first lock detection

## Verification

1. Run `erk plan submit <issue>` and observe per-attempt output during workflow run polling
2. Run `erk pr submit` and observe Graphite cache polling message
3. Run unit tests for affected files to ensure no regressions
