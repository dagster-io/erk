# Fix: Address dispatch not updating run_id/run_status in TUI

## Context

When pressing "a" in the TUI to dispatch `address_remote`, the `run_id` and `run_status` columns never update. Two compounding issues:

1. `--no-wait` causes `maybe_write_pending_dispatch_metadata()` to write `node_id=None`, so the plan list service skips the plan when fetching workflow runs.
2. No `action_refresh()` call after dispatch, unlike `_close_plan_async` (line 529) which does refresh.

## Changes

**`src/erk/tui/app.py`** — `_address_remote_async()` (lines 539-559):

1. **Remove `"--no-wait"` from subprocess args** (line 544): Without `--no-wait`, the CLI polls for the real `run_id` (~5-30s). Since this runs in a `@work(thread=True)` worker, the wait does not block the TUI.

2. **Add `self.call_from_thread(self.action_refresh)` after the success toast** (after line 551): Matches the pattern used by `_close_plan_async` at line 529.

```python
# Line 544: remove "--no-wait"
["erk", "launch", "pr-address", "--pr", str(pr_number)],

# After line 551: add refresh
self.call_from_thread(self.action_refresh)
```

## Verification

1. `ruff check src/erk/tui/app.py` — no lint errors
2. `ty check src/erk/tui/app.py` — no type errors
3. Run existing TUI tests: `pytest tests/tui/`
4. Manual: `erk dash` → select plan with PR comments → Space → "a" → confirm run_id/run_status update after ~5-30s
