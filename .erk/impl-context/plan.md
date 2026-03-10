# Hide `learn` Command in CLI Help Output

## Context

The `learn` command currently appears under "Other:" in `erk -h` output. It should be hidden from default help output and only appear under "Hidden:" when `show_hidden_commands` is enabled in config, matching the pattern used by `reconcile`.

## Changes

### File: `src/erk/cli/commands/learn/learn_cmd.py`

**Line 62**: Add `hidden=True` to the `@click.command` decorator.

Change:
```python
@click.command("learn")
```

To:
```python
@click.command("learn", hidden=True)
```

This is the only code change required. The existing `ErkCommandGroup` help formatter in `src/erk/cli/help_formatter.py` already handles hidden commands — it collects them into a "Hidden:" section when `show_hidden_commands` is True in config, and excludes them entirely when False. No changes to the formatter or CLI registration (`cli.py` line 199) are needed.

## Files NOT Changing

- `src/erk/cli/cli.py` — The `cli.add_command(learn_cmd)` registration at line 199 stays as-is. Click's `hidden=True` on the command itself is sufficient; the `ErkCommandGroup.format_commands` method already checks `cmd.hidden` to categorize commands.
- `src/erk/cli/help_formatter.py` — No formatter changes needed. The hidden command infrastructure already works correctly (as proven by `reconcile`).
- `tests/` — No test changes needed. The existing `test_help_formatter.py` tests validate the hidden command infrastructure generically. The `learn` command doesn't have specific visibility tests.
- `CHANGELOG.md` — Never modified directly per project conventions.

## Verification

1. Run `ruff check src/erk/cli/commands/learn/learn_cmd.py` — should pass with no errors
2. Run `ty check src/erk/cli/commands/learn/learn_cmd.py` — should pass type checking
3. Run `pytest tests/unit/cli/test_help_formatter.py` — existing hidden command tests should still pass
4. Run `pytest tests/commands/learn/` — existing learn command tests should still pass
5. Manual verification: `erk -h` should no longer show `learn` under "Other:". With `show_hidden_commands: true` in config, `erk -h` should show `learn` under "Hidden:".