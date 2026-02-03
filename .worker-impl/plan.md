# Plan: Fix help text formatting for erk init capability commands

> **Replans:** #6601

## What Changed Since Original Plan

- Investigation confirmed the original plan is accurate - no codebase drift
- Discovered `add_cmd.py` has the same formatting bug (not in original plan)

## Investigation Findings

### Corrections to Original Plan
- None - file path, line number, and solution are all correct

### Additional Details Discovered
- `src/erk/cli/commands/init/capability/add_cmd.py` has the identical problem (missing `\b` before Examples)
- Pattern is well-established across the codebase: `implement.py`, `launch_cmd.py`, `delete_cmd.py`, `submit_cmd.py` all use `\b` correctly

## Implementation Steps

1. **Fix `remove_cmd.py`** (`src/erk/cli/commands/init/capability/remove_cmd.py`)
   - Add `\b` on its own line before line 24 (`Examples:`)
   - Verification: `erk init capability remove --help` shows examples on separate lines

2. **Fix `add_cmd.py`** (`src/erk/cli/commands/init/capability/add_cmd.py`)
   - Add `\b` on its own line before line 25 (`Examples:`)
   - Verification: `erk init capability add --help` shows examples on separate lines

## Verification

```bash
erk init capability remove --help   # Examples should appear on separate indented lines
erk init capability add --help      # Same check
```