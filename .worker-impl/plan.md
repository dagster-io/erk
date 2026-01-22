# Plan: Increase Timeout for Landing PR in TUI

## Problem

When landing a PR from the TUI dashboard, the objective update operation times out after 30 seconds. The screenshots show:
- "Command timed out after 30 seconds" during the objective update phase
- The Claude agent running `/erk:objective-update-with-landed-pr` doesn't have enough time to complete

## Root Cause

There are **two code paths** for landing a PR:

1. **`plan_detail_screen.py:685-697`** - Has `timeout=600.0` (correct)
2. **`app.py:673-684`** - Missing timeout parameter, uses default 30 seconds (BUG)

The TUI uses the `app.py` path when executing the "land_pr" command from the command palette, which causes the 30-second timeout.

## Solution

Add `timeout=600.0` to the `run_streaming_command` call in `app.py` to match `plan_detail_screen.py`.

## Files to Modify

**`src/erk/tui/app.py:673-684`**

Add `timeout=600.0` to the call:
```python
detail_screen.call_after_refresh(
    lambda: detail_screen.run_streaming_command(
        [
            "erk",
            "exec",
            "land-execute",
            f"--pr-number={pr_num}",
            f"--branch={branch}",
            "-f",
        ],
        cwd=self._provider.repo_root,
        title=f"Landing PR #{pr_num}",
        timeout=600.0,  # ADD THIS LINE
    )
)
```

## Verification

1. Run existing tests: `make fast-ci`
2. Manual test: Use `erk dash -i` to open the TUI, select a PR linked to an objective, and land it. The objective update should complete without timing out.