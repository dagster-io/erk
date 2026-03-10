# Make `--stack` a Hidden Flag on `erk land`

## Context

The `--stack` flag on `erk land` should be hidden from normal help output. The infrastructure for hidden flags already exists via `CommandWithHiddenOptions`, and the `land` command already uses this class (for the existing hidden `--script` flag).

## Change

**File:** `src/erk/cli/commands/land_cmd.py` (line 1504)

Add `hidden=True` to the `--stack` option:

```python
@click.option(
    "--stack",
    "stack_flag",
    is_flag=True,
    hidden=True,
    help="Land the current Graphite stack bottom-up.",
)
```

That's it — single line addition. The `CommandWithHiddenOptions` class on the `land` command already handles showing/hiding based on `show_hidden_commands` config.

## Verification

1. `erk land --help` — `--stack` should NOT appear in normal options
2. Set `show_hidden_commands: true` in config → `erk land --help` should show `--stack` under "Hidden Options"
3. `erk land --stack` should still work functionally (hidden != removed)
