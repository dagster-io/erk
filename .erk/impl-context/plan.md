# Unify Launch Modal and Command Palette via Single Source of Truth

## Context

The TUI has two independent definitions of which ACTION commands are available for PR operations:

1. **Command registry** (`registry.py`): Defines 7 plan ACTION commands (close, dispatch, land, rebase, address, rewrite, cmux sync)
2. **Launch modal** (`launch_screen.py`): Has a separate `LAUNCH_KEYS` dict mapping only 5 of those to keyboard shortcuts (missing rewrite and cmux sync)

This means the command palette (Ctrl+P) shows all 7 actions while the Launch modal (L key) only shows 5. Adding a new ACTION command requires updating two files that can drift apart.

## Approach

Add a `launch_key: str | None` field to `CommandDefinition`. The registry becomes the single source of truth for both surfaces. Remove the separate `LAUNCH_KEYS` dict.

## Changes

### 1. `src/erk/tui/commands/types.py` — Add field to CommandDefinition

Add `launch_key: str | None` between `shortcut` and `is_available`.

### 2. `src/erk/tui/commands/registry.py` — Add launch_key to all command definitions

ACTION commands get their key letter; all others get `launch_key=None`.

Key assignments (existing preserved, new ones added):

| Command | Key | Status |
|---|---|---|
| close_plan | c | existing |
| dispatch_to_queue | d | existing |
| land_pr | l | existing |
| rebase_remote | f | existing |
| address_remote | a | existing |
| **rewrite_remote** | **w** | **new** |
| **cmux_sync** | **m** | **new** |
| close_objective | c | existing |
| one_shot_plan | s | existing |
| check_objective | k | existing |

### 3. `src/erk/tui/screens/launch_screen.py` — Remove LAUNCH_KEYS, use cmd.launch_key

Replace `LAUNCH_KEYS.get(cmd.id)` with `cmd.launch_key` in the init loop. Delete the `LAUNCH_KEYS` dict entirely.

### 4. `tests/tui/screens/test_launch_screen.py` — Update tests

- Remove `LAUNCH_KEYS` import
- Rewrite `test_launch_keys_only_maps_action_commands` to check `launch_key` is only set on ACTION commands via registry
- Rewrite duplicate-key tests to use `launch_key` field from registry
- Add `"w"` (rewrite_remote) assertion to plan view key mapping tests
- Add `"w"` assertion to `test_launch_screen_maps_command_ids_correctly`

### 5. `tests/tui/commands/test_registry.py` — Add launch_key safety tests

- Add test that `launch_key` values don't conflict within each view mode
- Add test that `launch_key` is only set on ACTION commands

## Verification

- Run `uv run pytest tests/tui/screens/test_launch_screen.py` — all launch screen tests pass
- Run `uv run pytest tests/tui/commands/test_registry.py` — all registry tests pass
- Run `uv run pytest tests/tui/` — full TUI test suite passes
- Manual: `erk dash -i`, press L on a plan row — should show rewrite (w) and cmux sync (m) in addition to existing options
