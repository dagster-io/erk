# Increase Log Panel Height in Plan Detail Screen

## Context

The `CommandOutputPanel` (shown when running commands like "Fix Conflicts Remote") is limited to 15 lines total / 10 lines of log content. Tracebacks and longer output get cut off, requiring scrolling in a tiny window. The user wants more room for logs.

## Changes

**File: `src/erk/tui/widgets/command_output.py`**

Increase the two `max-height` CSS values:

- `CommandOutputPanel` max-height: `15` → `25`
- `CommandOutputPanel #output-log` max-height: `10` → `20`

This gives the log content area double the space (20 visible lines instead of 10). The panel uses `height: auto` so it won't waste space when output is short — it only grows as needed up to the new max.

The parent `#detail-dialog` already has `max-height: 90%` and will scroll if the combined content exceeds the terminal height, so this is safe.

## Verification

- Run `erk dash -i`, open a plan detail, trigger a command (e.g. fix conflicts)
- Confirm the log panel shows more lines before requiring scroll
- Confirm the panel still auto-sizes for short output (doesn't waste space)
