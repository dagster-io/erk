# Plan: Change "Dispatch to Queue" shortcut from 's' to 'd'

## Context

The "Dispatch to Queue" (`submit_to_queue`) command in the TUI launch screen currently uses 's' as its keyboard shortcut. Change it to 'd' for better mnemonics (d = dispatch).

## Changes

### 1. `src/erk/tui/commands/registry.py` (line 202)
- Change `shortcut="s"` to `shortcut="d"` on the `submit_to_queue` CommandDefinition

### 2. `src/erk/tui/screens/launch_screen.py` (line 22)
- Change `"submit_to_queue": "s"` to `"submit_to_queue": "d"` in `LAUNCH_KEYS`

### 3. `tests/tui/screens/test_launch_screen.py` (3 assertions)
- Line 56: `"s"` → `"d"` (`test_launch_screen_builds_key_mapping_for_plan_view`)
- Line 98: `"s"` → `"d"` (`test_launch_screen_excludes_unavailable_commands`)
- Line 120: `"s"` → `"d"` (`test_launch_screen_maps_command_ids_correctly`)

Note: The objectives-view `one_shot_plan` command also uses `"s"` in both `LAUNCH_KEYS` and `registry.py` — those remain unchanged since they're in a different view context and the summary only targets the dispatch command.

## Verification

Run: `uv run pytest tests/tui/screens/test_launch_screen.py`
