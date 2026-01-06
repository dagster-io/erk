# Plan: Make "Close Plan" Action Non-Blocking in erk dash

## Problem

The "Close Plan" action in `erk dash` runs synchronously and locks up the UI while closing linked PRs and the issue via GitHub API. Users think the app is frozen.

## Solution

Use the same streaming command pattern that "Submit to Queue" uses - run `erk plan close` via `run_streaming_command()` which:
1. Shows a `CommandOutputPanel` immediately
2. Runs the subprocess in a background thread
3. Streams output line-by-line to the panel
4. Shows completion status when done

## Files to Modify

### `src/erk/tui/app.py` (~lines 673-684)

**Before:**
```python
elif command_id == "close_plan":
    if row.issue_url:
        closed_prs = executor.close_plan(row.issue_number, row.issue_url)
        if closed_prs:
            pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
            executor.notify(f"Closed plan #{row.issue_number} and PRs: {pr_list}")
        else:
            executor.notify(f"Closed plan #{row.issue_number}")
        executor.refresh_data()
        if self.is_attached:
            self.dismiss()
```

**After:**
```python
elif command_id == "close_plan":
    if row.issue_url and self._repo_root is not None:
        # Use streaming output for close command
        self.run_streaming_command(
            ["erk", "plan", "close", str(row.issue_number)],
            cwd=self._repo_root,
            title=f"Closing Plan #{row.issue_number}",
        )
        # Don't dismiss - user must press Esc after completion
```

## Behavior After Change

1. User selects "Close Plan" action
2. Panel immediately appears with title "Closing Plan #123"
3. Output streams: "Closed plan #123", "Closed 2 linked PR(s): #456, #789"
4. Panel shows "✓ Complete - Press Esc to close, y to copy logs"
5. Data refreshes when user presses Esc (handled by existing `action_dismiss()` logic)

## Testing

The existing test infrastructure for `run_streaming_command` applies. May want to add a unit test confirming the command array is correct.

## Related Documentation

- `docs/learned/tui/TEXTUAL_QUIRKS.md` - Textual API patterns