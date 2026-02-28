---
title: TUI Subprocess Feedback Patterns
read_when:
  - "adding subprocess calls to the TUI"
  - "implementing background worker feedback in the TUI"
  - "parsing subprocess stderr for status markers"
tripwires:
  - action: "adding a subprocess call to the TUI without stderr inspection"
    warning: "TUI subprocess calls should inspect stderr for known success/failure markers. See subprocess-feedback.md for the pattern."
---

# TUI Subprocess Feedback Patterns

The TUI executes subprocess commands in background workers and provides feedback to users via `self.notify()`. A consistent pattern is used across all subprocess-calling methods.

## Subprocess Error Extraction

<!-- Source: src/erk/tui/app.py -->

A helper function extracts human-readable error messages from the operation result object:

1. Iterate backwards through the output lines (merged stdout/stderr)
2. Return the first non-empty line found
3. Fall back to `"Unknown error"` if all lines are empty

## Stderr Inspection for Status Markers

TUI background workers check `result.stderr` for specific success markers after subprocess calls. For example, the address-remote handler checks for `"Updated dispatch metadata"` in stderr to confirm a workflow dispatch succeeded.

This pattern is necessary because subprocess exit code 0 alone doesn't distinguish between "successfully dispatched" and "silently did nothing."

## Standard Pattern

All TUI subprocess methods follow this structure:

1. Run `subprocess.Popen` with `stderr=subprocess.STDOUT` (merged streams), `stdin=subprocess.DEVNULL`, streaming output line-by-line into an operation result object
2. On success (`return_code == 0`): check output lines for expected success markers, notify with `severity="information"` (3s timeout)
3. On failure (`return_code != 0`): extract the last non-empty output line as the error message, notify with `severity="error"` (5s timeout)
4. Trigger `self.action_refresh()` to update the display after state changes

This pattern is used across multiple async subprocess methods in the TUI app, including the address-remote, fix-conflicts-remote, and land-PR handlers.

## Known Gap: CLI-Side Diagnostic Output

CLI-side diagnostic output via `user_output` warnings was implemented in PR #8078 but subsequently reverted in commit a50fa13f2 (which eliminated the `--no-wait` flag and `dispatch_workflow()` method). The silent failure problem — where a dispatch succeeds but produces no user-visible feedback — remains a known gap. The TUI-side stderr inspection partially mitigates this, but CLI users don't benefit from it.

## Related Documentation

- [TUI Subprocess Testing](../testing/tui-subprocess-testing.md) — Testing patterns for TUI subprocess calls
- [Error Detection Patterns](../cli/error-detection-patterns.md) — Keyword detection for parsing subprocess stderr
