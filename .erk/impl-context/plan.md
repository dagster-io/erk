# Plan: Add Launch Screen to erk dash TUI

## Context

The erk dash TUI currently requires either Ctrl+P (command palette with fuzzy search) or Enter (detail modal with many bindings) to execute ACTION commands. This is too many keystrokes for frequent operations like submit, fix-conflicts, and address. The goal is two-keystroke execution: press `l` to open a compact launch menu, then a single key to fire the action.

## Approach

Create a new `LaunchScreen` modal (following the `HelpScreen` pattern) that filters to ACTION-category commands and assigns each a single key. The screen uses Textual's `ModalScreen[str | None]` dismiss-with-result pattern so the app's existing `execute_palette_command()` handles all execution.

## Files

### New: `src/erk/tui/screens/launch_screen.py`

- `LaunchScreen(ModalScreen[str | None])` - takes `CommandContext`
- `LAUNCH_KEYS` constant mapping command_id to single key:
  - Plan actions: `c`=close, `s`=submit, `l`=land, `f`=fix-conflicts, `a`=address
  - Objective actions: `c`=close, `s`=plan(one-shot), `k`=check
- On `compose()`: filters `get_available_commands(ctx)` to `CommandCategory.ACTION`, builds `_key_to_command_id` dict, renders each as a labeled row with format: `  [key]  ⚡ description: display_name`
- `on_key()` catch-all handler: if pressed key is in `_key_to_command_id`, calls `self.dismiss(command_id)`
- `action_dismiss_cancel()` for Escape/q: calls `self.dismiss(None)`
- Inline `DEFAULT_CSS` styled like `HelpScreen` (centered modal, `$surface` bg, `$primary` border, width ~72)

### Modify: `src/erk/tui/app.py`

- Add import: `LaunchScreen`, `CommandContext`
- Add binding: `Binding("l", "launch", "Launch")` to `BINDINGS` list
- Add `action_launch()`: get selected row, build `CommandContext`, push `LaunchScreen` with callback
- Add `_on_launch_result(command_id: str | None)`: if not None, call `self.execute_palette_command(command_id)`

### Modify: `src/erk/tui/screens/help_screen.py`

- Add `"l       Launch actions menu"` to the Actions section

## Execution Flow

1. User presses `l` on main list
2. `action_launch()` builds `CommandContext` from selected row + view mode + plan backend
3. `push_screen(LaunchScreen(ctx=ctx), self._on_launch_result)` opens modal
4. LaunchScreen shows only available ACTION commands (filtered by `is_available` predicates)
5. User presses action key (e.g., `f` for fix-conflicts)
6. `on_key()` matches, calls `self.dismiss("fix_conflicts_remote")`
7. Textual delivers result to `_on_launch_result`
8. `execute_palette_command("fix_conflicts_remote")` runs existing handler (streaming detail, async close, etc.)

## Key Reuse Across Views

Plan keys (c/s/l/f/a) and objective keys (c/s/k) can reuse letters because `get_available_commands` already filters by view mode - plan commands only appear in Plans/Learn views, objective commands only in Objectives view.

## Verification

1. Run `erk dash -i`, select a plan row, press `l` - launch screen should appear
2. Press `s` - should dismiss and trigger submit (streaming output in detail modal)
3. Press `f` - should dismiss and trigger fix-conflicts remote
4. Press `Esc` - should dismiss with no action
5. Select a row with no PR, press `l` - fix-conflicts and address should not appear
6. Switch to Objectives view, press `l` - should show objective actions (plan, check, close)
7. Run tests: `pytest tests/tui/screens/test_launch_screen.py`
