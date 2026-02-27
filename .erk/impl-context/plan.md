# Fix remaining `issue_number` → `plan_number` in test_log.py

## Context

The branch `plnd/O7724-rename-to-plan-numbe-02-27-0227` renames `issue_number` to `plan_number` in plan-specific gateway methods. The production code is fully renamed, but 4 call sites in `tests/commands/pr/test_log.py` still pass the old `issue_number` keyword argument, causing 3 test failures.

## Changes

**File: `tests/commands/pr/test_log.py`**

4 keyword argument renames (all `issue_number=42` → `plan_number=42`):

1. **Line 69** — `create_workflow_started_block(... issue_number=42)` in `test_log_displays_timeline_chronologically`
2. **Line 81** — `create_submission_queued_block(... issue_number=42)` in `test_log_displays_timeline_chronologically`
3. **Line 253** — `create_submission_queued_block(... issue_number=42)` in `test_log_with_all_event_types`
4. **Line 261** — `create_workflow_started_block(... issue_number=42)` in `test_log_with_all_event_types`

No other changes needed.

## Verification

Run: `make all-ci` — all 3 failing tests should pass, bringing the suite to 5359/5359 passing.
