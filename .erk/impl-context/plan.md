# Make `erk reconcile` a Hidden Command

## Context

The `erk reconcile` command detects and cleans up branches whose PRs were merged outside of `erk land`. It's a useful maintenance command but not a high-frequency workflow entry point. Currently it shows up in the "Other" section of `erk --help` output because it's not categorized in the help formatter's command lists and doesn't have `hidden=True`.

Making it hidden removes it from default help output, reducing noise for users. It will still be visible when `show_hidden_commands=True` is configured, and remains fully functional.

## Changes

### 1. `src/erk/cli/commands/reconcile_cmd.py`

Add `hidden=True` to the `@click.command` decorator on line 23:

**Before:**
```python
@click.command("reconcile")
```

**After:**
```python
@click.command("reconcile", hidden=True)
```

This is the only code change needed. The `ErkCommandGroup.format_commands()` method in `help_formatter.py` already handles hidden commands correctly — commands with `hidden=True` are excluded from help output by default and shown in a "Hidden" section when `show_hidden_commands` is enabled in config.

## Files NOT Changing

- `src/erk/cli/cli.py` — No change needed. The `cli.add_command(reconcile)` registration on line 195 works the same regardless of hidden status.
- `src/erk/cli/help_formatter.py` — No change needed. The existing logic at line 219 (`effectively_hidden = cmd.hidden or ...`) already handles `hidden=True` commands.
- `tests/commands/test_reconcile.py` — No change needed. Tests invoke the command directly via `CliRunner`, which doesn't depend on help visibility. The command's functionality is unchanged.
- `docs/learned/cli/commands/reconcile.md` — No change needed. The doc describes behavior and implementation, not visibility.

## Implementation Details

- The pattern follows exactly what was done for `prepare_cwd_recovery` (`hidden=True` on `@click.command`) and the `exec` group (`hidden=True` on `@click.group`).
- The `codespace` group and `wt current` command also use this same pattern.
- This is a one-line change with no behavioral impact beyond help output.

## Verification

1. Run `erk --help` and confirm `reconcile` does NOT appear in the output
2. Run `erk reconcile --help` and confirm the command still works (hidden commands are still invocable)
3. Run existing tests: `pytest tests/commands/test_reconcile.py` — should all pass unchanged
4. Run help formatter tests: `pytest tests/unit/cli/test_help_formatter.py` — should all pass unchanged