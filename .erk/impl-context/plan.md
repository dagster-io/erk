# Improve `erk pr submit` Performance

## Context

`erk pr submit` runs an 11-step linear pipeline that makes many redundant network calls and runs independent steps sequentially. The pipeline accumulates GitHub API calls, Graphite auth checks, and branch lookups that duplicate work already done in earlier steps. This plan addresses the low-hanging fruit for performance improvement.

## Key Files

- `src/erk/cli/commands/pr/submit_pipeline.py` — Main pipeline (all steps)
- `src/erk/cli/commands/pr/submit_cmd.py` — CLI entry point + PR cache polling
- `packages/erk-shared/src/erk_shared/gateway/pr/graphite_enhance.py` — Graphite check

## Problem Analysis

### 1. Redundant GitHub API Calls (biggest win)

The pipeline makes up to **7 separate GitHub API calls** for PR info, many redundant:

| Line | Call | Purpose | Redundant? |
|------|------|---------|------------|
| 229 | `get_pr_for_branch` | Capture existing PR body | Needed |
| 332 | `get_pr_for_branch` | Get PR after gt submit | Needed |
| 458 | `get_pr_for_branch` | Check existing PR (core flow) | Needed |
| 495 | `get_pr` | Get PR URL after create | **Yes** — URL can be constructed |
| 523 | `get_pr` | Check for footer (existing PR) | Needed |
| 770 | `get_pr` | Check draft status | Needed |
| 823 | `get_pr_for_branch` | Get "final" PR URL | **Yes** — already in state |

**Fix:** Remove line 823 (`get_pr_for_branch` at end of `finalize_pr`) — `state.pr_url` is already set by `push_and_create_pr`. Remove the `get_pr` at line 495 — construct URL from repo info instead.

### 2. Redundant Auth & Branch Checks

- `should_enhance_with_graphite` (called in `push_and_create_pr`) re-does `check_auth_status`, `get_repository_root`, `get_current_branch`, and `get_all_branches` — all already resolved by `prepare_state`
- `enhance_with_graphite` (line 663) calls `check_auth_status` again
- `finalize_pr` (line 829) calls `check_auth_status` a third time

**Fix:** Cache graphite auth result and branch tracking status in `SubmitState` during `prepare_state`, pass it through instead of re-checking. Or refactor `should_enhance_with_graphite` to accept pre-resolved values.

### 3. Sequential Independent Steps

`extract_diff` and `fetch_plan_context` are completely independent but run sequentially. Together they add 500-2500ms of wall time.

**Fix:** Run them concurrently using `concurrent.futures.ThreadPoolExecutor`. Both are I/O-bound (git diff + GitHub API), making threading appropriate.

### 4. PR Cache Polling (up to 10s)

After submit, the pipeline polls Graphite cache for up to 10 seconds (`_wait_for_pr_in_cache`). This is purely for status line display.

**Fix:** Either reduce the timeout, make it non-blocking, or skip it when the status line isn't active. Could also run it in a background thread.

### 5. `_core_submit_flow` Redundancy

In the core flow for existing PRs (line 523), it calls `get_pr` to check the footer, even though `capture_existing_pr_body` already fetched the PR body. The existing body is in `state.existing_pr_body`.

**Fix:** Use `state.existing_pr_body` to check for footer instead of making another API call.

## Recommended Changes (This PR)

### Change 1: Eliminate Redundant API Calls in `finalize_pr`

In `finalize_pr`, remove the `get_pr_for_branch` call at the end (line 823). The `pr_url` is already set by `push_and_create_pr` and doesn't change. Just use `state.pr_url`.

Similarly, remove the `check_auth_status` + `get_graphite_url` block at lines 828-834 — `graphite_url` is already set by either `_graphite_first_flow` or `enhance_with_graphite`.

### Change 2: Use `state.existing_pr_body` for Footer Check

In `_core_submit_flow` (line 523), when checking for an existing PR's footer, use `state.existing_pr_body` from `capture_existing_pr_body` instead of calling `get_pr` again. Requires checking that the existing body was captured for this PR.

### Change 3: Cache Graphite Check Results

Add `graphite_is_authed` and `graphite_branch_tracked` fields to `SubmitState`. Populate them once during `prepare_state`. Use these cached values in `push_and_create_pr`, `enhance_with_graphite`, and `finalize_pr` instead of re-calling `check_auth_status` and `get_all_branches`.

## Follow-on Work (separate PRs)

- Parallelize `extract_diff` + `fetch_plan_context` with ThreadPoolExecutor
- Reduce PR cache polling from 10s to 3s or make conditional

## Verification

1. Run `erk pr submit` on a branch with changes and verify it still creates/updates PRs correctly
2. Run `erk pr submit --skip-description` to verify the fast path
3. Run `erk pr submit --no-graphite` to verify the core flow
4. Run existing tests: `pytest tests/ -k submit`
5. Time before/after with `time erk pr submit` to measure improvement
