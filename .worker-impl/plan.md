# Plan: Command Palette Description Prefixes with Dimmed Command Text

## Summary

Add one-word description prefixes to all command palette items, dim the command text portion, and remove the `copy_prepare_dangerous` command.

Display format: `{emoji} {description}: {command_text}` where description is bright and command_text is dimmed.

## Description Mapping

| Command ID | Description |
|---|---|
| close_plan | close |
| submit_to_queue | submit |
| land_pr | land |
| fix_conflicts_remote | fix-conflicts |
| address_remote | address |
| open_issue | plan |
| open_pr | pr |
| open_run | run |
| copy_checkout | checkout |
| copy_pr_checkout | sync |
| copy_prepare | prepare |
| copy_prepare_activate | implement |
| copy_submit | submit |
| copy_replan | replan |

`copy_prepare_dangerous` is removed entirely.

## Changes

### 1. `src/erk/tui/commands/registry.py` — Update descriptions, remove dangerous, fix Opens

- Update all `description=` values to the one-word labels above
- Delete `_display_copy_prepare_dangerous` function
- Delete `copy_prepare_dangerous` CommandDefinition from `get_all_commands()`
- Fix Opens display names to drop embedded prefix (provider will add it):
  - `_display_open_issue`: return `ctx.row.issue_url` (not `f"plan: {url}"`)
  - `_display_open_pr`: return `ctx.row.pr_url` (not `f"pr: {url}"`)
  - `_display_open_run`: return `ctx.row.run_url` (not `f"run: {url}"`)

### 2. `src/erk/tui/commands/provider.py` — Styled display with dim command text

Replace `_format_highlighted_display` with two new functions:

**`_format_palette_display(emoji, label, command_text)`** — For `discover()`:
- Returns `Text.assemble(f"{emoji} ", f"{label}: ", (command_text, "dim"))`

**`_format_search_display(emoji, highlighted, label_len)`** — For `search()`:
- Splits highlighted Text at `label_len`, applies `"dim"` to command portion
- Preserves fuzzy-match highlights within dim text

Update both `MainListCommandProvider` and `PlanCommandProvider`:
- `discover()`: use `_format_palette_display(emoji, cmd.description, name)`
- `search()`: match against `f"{cmd.description}: {name}"`, then use `_format_search_display`

### 3. `src/erk/tui/screens/plan_detail_screen.py` — Remove dangerous

- Remove `Binding("2", "copy_prepare_dangerous", "Dangerous")` (line 50)
- Remove `action_copy_prepare_dangerous` method (lines 345-348)
- Remove `elif command_id == "copy_prepare_dangerous":` block (lines 645-648)
- Remove dangerous command display in `compose()` (lines 835-838)

### 4. `src/erk/tui/app.py` — Remove dangerous handler

- Remove `elif command_id == "copy_prepare_dangerous":` block (lines 589-592)

### 5. Tests

**`tests/tui/commands/test_registry.py`:**
- Remove `test_display_name_copy_prepare_dangerous_shows_issue_and_flag`
- Update `test_prepare_commands_always_available`: remove `copy_prepare_dangerous` assertion
- Update Open display name tests to expect bare URLs (no prefix)
- Add test: all commands have non-empty description (already exists, values just change)

**`tests/tui/commands/test_execute_command.py`:**
- Remove `test_copy_prepare_dangerous_copies_command`

**`tests/tui/test_app.py`:**
- Remove `test_copy_prepare_dangerous_shortcut_2`

**Add new test** for palette display formatting (in test_registry.py or new file):
- Verify `_format_palette_display` produces correct `Text` with dim styling

## Verification

1. Run `pytest tests/tui/` to verify all test changes pass
2. Run `ruff check` and `ty check` on changed files
3. Manual: `erk dash -i`, Ctrl+P to open palette, verify:
   - Each item shows `description: command` format
   - Description text is bright, command text is dimmed
   - `copy_prepare_dangerous` no longer appears
   - Fuzzy search works (typing "close" or "prepare" finds correct commands)
   - Plan detail screen (Enter on a row) no longer has "2" shortcut for dangerous