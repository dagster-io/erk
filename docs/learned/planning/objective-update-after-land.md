---
title: Objective Update After Land
read_when:
  - "modifying the land pipeline's post-merge behavior"
  - "working with objective-update-after-land exec script"
  - "understanding fail-open patterns in erk"
tripwires:
  - action: "making objective-update-after-land exit non-zero"
    warning: "This script uses fail-open design. Failures must not block landing. See objective-update-after-land.md."
---

# Objective Update After Land

After landing a PR, the associated objective issue needs updating. This is handled by the `objective-update-after-land` exec script.

## Location

`src/erk/cli/commands/exec/scripts/objective_update_after_land.py`

## Fail-Open Design

The script always exits 0. The merge has already succeeded at this point — objective update failures must not block the landing workflow.

**Rationale**: The merge is the critical operation; objective tracking is secondary. A failed objective update can always be retried manually.

## How It Works

1. Click command takes three required options: `--objective`, `--pr`, `--branch`
2. Builds a command string for the `/erk:objective-update-with-landed-pr` slash command
3. Executes via `stream_command_with_feedback()` with `permission_mode="edits"` and `dangerous=True`
4. Returns `CommandResult` — handles both success and error cases without raising

## Activation

Called from the land pipeline after a successful merge. The land pipeline invokes this as a post-merge step.

## Related Topics

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Related error handling patterns
