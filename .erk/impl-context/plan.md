# Plan: Add Active Workflow Run Indicator to Statusline

> **Replans:** #8668

## Context

When erk dispatches a plan for remote implementation via GitHub Actions, there's no visual indication in the statusline that a workflow is actively running. This plan adds a robot emoji (🤖) indicator showing active workflow runs for the current PR, giving users real-time awareness of remote agent activity.

## What Changed Since Original Plan

- Plan #8668 was closed without implementation — all items remain unimplemented
- Codebase is unchanged relative to the plan's assumptions
- Line numbers verified accurate as of current master

## Investigation Findings

### Corrections to Original Plan

1. **Line references slightly off**: `max_workers=3` is at line 795 (plan said 794), `_fetch_review_thread_counts` ends at line 737
2. **Missing early-return path**: The `GitHubData` constructor at lines 772-782 (no-PR case) must also include `active_run_count=0`
3. **Missing TimeoutError path**: Line 821 must set `active_run_count = 0`

### Key Architecture Details

- **GitHubData** is a `NamedTuple` at lines 134-145 with 9 fields. Adding `active_run_count: int = 0` as trailing default preserves all existing constructors
- **Parallel fetch** uses `ThreadPoolExecutor(max_workers=3)` at line 795 with 3 futures
- **`build_gh_label`** receives `github_data: GitHubData | None` — the new field is accessible without signature changes
- **Workflow run-name patterns** use `:#PR_NUMBER:` format (verified in plan-implement.yml, pr-address.yml, one-shot.yml, pr-rebase.yml, pr-rewrite.yml). learn.yml correctly excluded (no `:#` pattern)

## Implementation Steps

### 1. Extend `GitHubData` NamedTuple (`statusline.py:134-145`)
- Add `active_run_count: int = 0` after `from_fallback` (line 145)
- Trailing default means all existing positional constructors continue working

### 2. Add `_fetch_active_workflow_runs()` function (`statusline.py`, after line 737)
- New function following `_fetch_review_thread_counts()` pattern
- Two sequential `gh api` REST calls: `repos/{owner}/{repo}/actions/runs?status=in_progress&per_page=20` and `...?status=queued&per_page=20`
- Filter `workflow_runs[].display_title` for pattern `:#PR_NUMBER:`
- Share combined 1.5s timeout budget — track elapsed time after first call, compute remaining before second
- Return `int` count, default to 0 on any error/timeout
- Include debug logging matching existing pattern

### 3. Add parallel worker for workflow runs (`statusline.py:795-813`)
- Bump `max_workers=3` to `max_workers=4` (line 795)
- Add `runs_future = executor.submit(lambda: _fetch_active_workflow_runs(...))` after threads_future
- Add `active_run_count = runs_future.result(timeout=2)` after review_thread_counts result
- Initialize `active_run_count = 0` before the try block

### 4. Update `GitHubData` construction paths
- **No-PR early return** (line 772-782): Add `active_run_count=0`
- **TimeoutError handler** (line 821): Add `active_run_count = 0`
- **Normal return** (line 836-846): Add `active_run_count=active_run_count`
- **Debug log** (line 826): Add run count to format string

### 5. Add robot emoji to `build_gh_label()` (`statusline.py:1142`)
- After comment count display (line 1142), before the `else` branch:
  ```python
  if github_data and github_data.active_run_count > 0:
      parts.extend([Token(" "), Token("🤖", color=Color.CYAN)])
  ```

### 6. Rename `gh:` prefix to `pr:` (`statusline.py`)
- Line 1082: `Token("(gh:")` → `Token("(pr:")`
- Line 1080: Update docstring example
- `README.md` line 16: Update example

### 7. Add tests (`test_statusline.py`)
- New `TestFetchActiveWorkflowRuns` class testing:
  - Successful detection with matching run names
  - No matches when no active runs
  - Timeout handling returns 0
  - Error handling returns 0
  - Filter excludes learn.yml (no `:#` pattern)
  - Multiple active runs counted correctly
- Update `TestBuildGhLabel` tests at lines 368, 383, 388, 413, 443: `(gh:` → `(pr:`
- Add tests for robot emoji presence/absence in `build_gh_label`

## Files to Modify

| File | Changes |
|------|---------|
| `packages/erk-statusline/src/erk_statusline/statusline.py` | Extend NamedTuple, add fetch function, bump workers, add emoji, rename prefix |
| `packages/erk-statusline/tests/test_statusline.py` | New test class, prefix updates, emoji tests |
| `packages/erk-statusline/README.md` | Update example output |

## Verification

1. Run `make fast-ci` to verify all existing tests pass with prefix rename
2. Run new workflow run tests specifically
3. Manual verification: check statusline output with/without active workflow runs
