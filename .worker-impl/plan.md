# Plan: Add a Print Statement

> **Replans:** #4892

## What Changed Since Original Plan

- Nothing has changed - the original plan has not been implemented yet

## Investigation Findings

### Corrections to Original Plan

- None - the original plan is accurate

### Additional Details Discovered

- The `cli()` function is at lines 162-179 in `src/erk/cli/main.py`
- Function body starts at line 167 (after decorators on lines 162-166)
- First line of body is `if debug:` at line 168
- The file uses `click.echo()` for output, not `print()` - but the plan specifically asks for `print()`

## Remaining Gaps

- The entire plan is unimplemented - need to add `print("hello")` to the `cli()` function

## Implementation Steps

1. Edit `src/erk/cli/main.py` line 167-168 to add `print("hello")` as the first line of the `cli()` function body (before the `if debug:` check)

## Files to Modify

- `src/erk/cli/main.py`

## Verification

Run `erk --help` and observe "hello" printed to stdout before the help output.