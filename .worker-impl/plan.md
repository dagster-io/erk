# Fix Inaccurate Graphite Command References in pr sync

## Problem

The `erk pr sync` command displays and documents `gt land` as a valid Graphite command, but `gt land` does not exist. The correct command is `gt merge`.

## File to Modify

`src/erk/cli/commands/pr/sync_cmd.py`

## Changes

1. **Line 4** - Module docstring: Change "gt land" → "gt merge"
2. **Line 74** - Command docstring: Change "gt land" → "gt merge"
3. **Lines 87-88** - Examples section: Change `gt land` → `gt merge`
4. **Line 181** - User output message: Change "gt pr, gt land, etc." → "gt merge, gt pr, etc."

## Verification

Run `gt merge --help` and `gt land --help` to confirm:
- `gt merge` - Valid command that merges PRs via Graphite
- `gt land` - Invalid command (shows full help, not command-specific help)