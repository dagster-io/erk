Make the `learn` command hidden in the CLI help output.

Currently `learn` appears under "Other:" in `erk -h`. It should appear under "Hidden:" instead, like `reconcile` does.

The command is registered in `src/erk/cli/cli.py` around line 199. Look at how `reconcile` is made hidden and apply the same pattern to `learn`.

