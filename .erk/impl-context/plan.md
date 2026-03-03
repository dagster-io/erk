# Add Active Workflow Run Indicator to Statusline

## Context

Erk dispatches GitHub Actions workflows (plan-implement, pr-address, one-shot, pr-rebase, pr-rewrite) to do remote AI work on PRs. Currently there's no visibility in the statusline about whether a remote agent is actively working on the current PR. This feature adds a robot emoji indicator when active workflow runs are detected.

Also renames the `gh:` prefix to `pr:` for clarity — the label shows PR info, not generic GitHub info.

**Target display:**
```
(pr:#8662 st:👀 chks:[🔄:2] cmts:✓ 🤖)
```

## Detection Strategy

All erk-dispatched workflows targeting a PR include `:#PR_NUMBER:` in their `display_title` (via `run-name`):
- `plan-implement.yml`: `"<plan_id>:#<pr_number>:<distinct_id>"`
- `pr-address.yml`: `"pr-address:#<pr_number>:<distinct_id>"`
- `one-shot.yml`: `"one-shot:#<pr_number>:<distinct_id>"`
- `pr-rebase.yml`: `"rebase:#<pr_number>:<distinct_id>"`
- `pr-rewrite.yml`: `"rewrite:#<pr_number>:<distinct_id>"`

`learn.yml` and `ci.yml` do NOT match this pattern, so they are correctly excluded.

## Implementation

All changes in `/Users/schrockn/code/erk/packages/erk-statusline/`.

### 1. Add `_fetch_active_workflow_runs()` function

**File:** `src/erk_statusline/statusline.py` (after `_fetch_review_thread_counts`, ~line 737)

New function that:
- Makes two sequential `gh api` calls: one for `status=in_progress`, one for `status=queued`
- Shares a combined timeout budget (1.5s) — computes remaining time before each call
- Filters `workflow_runs[].display_title` for the pattern `:#PR_NUMBER:`
- Returns an `int` count of matching runs (0 on any error)

### 2. Extend `GitHubData` NamedTuple

**File:** `src/erk_statusline/statusline.py` (line 134)

Add trailing field with default: `active_run_count: int = 0`

Existing constructors continue to work unchanged since trailing defaults are supported.

### 3. Add 4th parallel worker in `fetch_github_data_via_gateway`

**File:** `src/erk_statusline/statusline.py` (line 794)

- Bump `max_workers=3` to `max_workers=4`
- Submit `_fetch_active_workflow_runs` as 4th future
- Collect result with `runs_future.result(timeout=2)`
- Default to `0` in the `TimeoutError` handler
- Pass `active_run_count` to `GitHubData` constructor (both normal return and early no-PR return)

### 4. Update `build_gh_label()` display

**File:** `src/erk_statusline/statusline.py` (after line 1142, before closing paren)

```python
if github_data is not None and github_data.active_run_count > 0:
    parts.extend([Token(" "), Token("🤖")])
```

### 5. Rename `gh:` → `pr:` prefix

- `statusline.py` line 1082: `Token("(gh:")` → `Token("(pr:")`
- `statusline.py` line 1080: update docstring example
- `README.md` line 16: update example
- `tests/test_statusline.py`: update `(gh:` → `(pr:` in all assertions (lines 368, 383, 388, 413, 443)

### 6. Tests

**File:** `tests/test_statusline.py`

- New `TestFetchActiveWorkflowRuns` class testing:
  - Counts matching runs across both in_progress and queued calls
  - Returns 0 when no runs match
  - Returns 0 on API failure
  - Does not match learn workflow pattern (`plan_id:distinct_id` without `:#`)
  - Handles timeout on first call gracefully
- Add `build_gh_label` tests for robot emoji presence/absence
- Add `_fetch_active_workflow_runs` to imports

No changes to existing tests needed for the new NamedTuple field (default value preserves compatibility).

## Performance

- Runs in parallel with existing 3 API calls — zero additional wall-clock time in typical case
- Two sequential `gh api` REST calls within 1.5s budget (~0.7s each)
- Returns `per_page=20` results (lightweight)
- No caching — each prompt gets fresh data (active run state changes rapidly)

## Verification

1. Run statusline tests: `cd packages/erk-statusline && pytest tests/`
2. Manual: dispatch a workflow run, verify 🤖 appears in statusline
3. Manual: after run completes, verify 🤖 disappears on next prompt
