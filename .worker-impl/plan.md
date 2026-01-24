# Fix: erk plan list not displaying [erk-learn] prefix in titles

## Problem

In `erk plan list` output, plan titles containing square brackets (like `[erk-learn]` prefixes) are not displayed. Rich interprets `[erk-learn]` as a style tag and strips it from the output.

This is the same issue that was fixed in the TUI in commit `248429afa`.

## Root Cause

In `src/erk/cli/commands/plan/list_cmd.py`, line 476 passes the title as a plain string to the Rich table. Rich parses strings for markup syntax, interpreting `[erk-learn]` as a style tag.

## Solution

Wrap the title in a `rich.text.Text` object, which prevents Rich from interpreting markup.

## Files to Modify

- `src/erk/cli/commands/plan/list_cmd.py`

## Implementation Steps

1. Add `Text` import from `rich.text`
2. Change row type hint from `list[str]` to `list[str | Text]`
3. Wrap title in `Text(title)`

### Specific Changes

**Line ~10**: Add import
```python
from rich.text import Text
```

**Lines 474-477**: Update row building
```python
# Build row based on which columns are enabled
row: list[str | Text] = [
    issue_id,
    Text(title),  # Prevent Rich markup interpretation
]
```

## Verification

1. Run `make fast-ci` to ensure tests pass
2. Run `erk plan list` and verify `[erk-learn]` prefixes are visible in titles