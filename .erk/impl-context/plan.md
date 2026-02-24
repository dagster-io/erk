# Plan: Show full command in address-remote toast

## Context

The `_address_remote_async` method in `src/erk/tui/app.py` (line 540) dispatches `erk launch pr-address --pr <N> --no-wait` and shows a toast saying "Dispatched address for PR #N". The user wants the toast to include the verbatim command that was run.

## Changes

**File: `src/erk/tui/app.py` (~line 543-551)**

1. Extract the command list into a local variable `cmd`
2. Build a display string with `shlex.join(cmd)` (or `" ".join(cmd)` since all args are simple)
3. Update the success toast to include the command: `f"Dispatched: {cmd_str}"`

The result toast will read something like:
```
Dispatched: erk launch pr-address --pr 8022 --no-wait
```

## Verification

- Run `erk dash -i`, trigger an address action, and confirm the toast shows the full command
