# Restore Land and Submit to Modals in TUI

## Context

Commits `873dc04bc` and `5d185bcb4` converted the "Land PR" and "Submit to Queue" TUI actions from blocking modal screens (with live streaming output) to non-blocking toast notifications with background workers. The user wants to revert to the modal pattern, where the user sees the command output in a `PlanDetailScreen` modal before returning to the table.

Other streaming commands (`fix_conflicts_remote`, `address_remote`, `one_shot_plan`, etc.) still use the modal pattern and serve as reference implementations.

## Changes

### 1. Extend `_push_streaming_detail` with `on_success` callback

**File:** `src/erk/tui/app.py` (line 644)

Add an optional `on_success: Callable[[], None] | None = None` parameter, passed through to `run_streaming_command`.

### 2. Replace land_pr handler with modal pattern

**File:** `src/erk/tui/app.py` (lines 1020-1028)

Replace:
```python
self.notify(f"Landing PR #{row.pr_number}...")
self._land_pr_async(...)
```

With `_push_streaming_detail` call using:
- Command: `["erk", "exec", "land-execute", f"--pr-number={pr_num}", f"--branch={branch}", "-f"]`
- Timeout: `600.0`
- `on_success`: callback that calls `action_refresh()` and triggers `_update_objective_async` if `row.objective_issue` is set

### 3. Replace submit_to_queue handler with modal pattern

**File:** `src/erk/tui/app.py` (lines 1015-1018)

Replace:
```python
self.notify(f"Submitting plan #{row.plan_id}...")
self._submit_to_queue_async(plan_id, self._provider.repo_root)
```

With `_push_streaming_detail` call using:
- Command: `["erk", "plan", "submit", str(row.plan_id), "-f"]`
- Timeout: `30.0`
- `on_success`: `self.action_refresh`

### 4. Extract objective update into standalone worker

**File:** `src/erk/tui/app.py`

Add `_update_objective_async` worker method (extracted from the objective update portion of `_land_pr_async`). This runs as a background worker with toast notifications for progress/success/failure.

### 5. Remove toast-based workers

**File:** `src/erk/tui/app.py`

Delete:
- `_land_pr_async` (lines 508-607)
- `_submit_to_queue_async` (lines 609-642)
- `_set_land_status` (lines 498-506)

### 6. Restore modal streaming in detail screen handlers

**File:** `src/erk/tui/screens/plan_detail_screen.py`

**land_pr** (lines 685-698): Replace dismiss+delegate pattern with `run_streaming_command` call (matching the `address_remote` pattern at line 660-665), with `on_success` for objective update + refresh.

**submit_to_queue** (lines 676-683): Replace dismiss+delegate pattern with `run_streaming_command` call, with `on_success` for refresh.

### 7. Update tests

**File:** `tests/tui/test_app.py`

- **TestExecutePaletteCommandLandPR**: Update `test_execute_palette_command_land_pr_calls_async_worker` to verify a `PlanDetailScreen` is pushed onto the screen stack (instead of verifying async worker call). Guard tests remain unchanged.
- **TestLandPrAsync**: Delete entire class (8 tests) - logic moves into PlanDetailScreen's streaming infrastructure which has its own test coverage.
- **TestExecutePaletteCommandSubmitToQueue**: Update `test_execute_palette_command_submit_to_queue_calls_async_worker` to verify modal push instead of async worker.
- **TestSubmitToQueueAsync**: Delete entire class (4 tests).
- **_FakePopen**: Remove if no longer referenced by remaining tests.

## Verification

1. Run TUI tests: `uv run pytest tests/tui/`
2. Run type checker on modified files
3. Manual test: `erk dash -i`, select a plan with a PR, run "Land PR" from palette - should show modal with streaming output
4. Manual test: select a plan, run "Submit to Queue" - should show modal with streaming output