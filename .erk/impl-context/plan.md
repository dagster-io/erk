# Add `-d` Shortcut for `--dangerous` Flag

## Context

The request is to add a `-d` shortcut/alias for the `--dangerous` flag on the `erk impl` command.

## Status: Already Implemented

Investigation reveals this work was **already completed** in commit `782ae4dbb` ("Add -d alias to all --dangerous flags (#5194)"). The `-d` shortcut exists in all commands that use `--dangerous`:

- `src/erk/cli/commands/implement_shared.py:92` — `implement_common_options` decorator (used by `erk implement`/`erk impl`)
- `src/erk/cli/commands/objective/plan_cmd.py:436` — `erk objective plan`
- `src/erk/cli/commands/learn/learn_cmd.py:71` — `erk learn`
- `src/erk/cli/commands/pr/reconcile_with_remote_cmd.py:16` — `erk pr reconcile-with-remote`
- `src/erk/cli/commands/pr/rebase_cmd.py:16` — `erk pr rebase`
- `src/erk/cli/commands/pr/address_cmd.py:16` — `erk pr address`
- `src/erk/cli/commands/branch/create_cmd.py:53` — `erk branch create`
- `src/erk/cli/commands/codespace/run/objective/plan_cmd.py:14` — `erk codespace run objective plan`

The current help output already shows `-d, --dangerous`:

```
Options:
  --dry-run         Print what would be executed without doing it
  --submit          Automatically run CI validation and submit PR after
                    implementation
  -d, --dangerous   Skip permission prompts by passing --dangerously-skip-
                    permissions to Claude
  ...
```

The documentation at `docs/learned/reference/cli-flag-patterns.md` already documents `-d` as the standard short form for `--dangerous`.

## Changes Required

**None.** No files need to be created or modified. The implementation is complete.

## Verification

Run to confirm:
```bash
uv run python -c "
from click.testing import CliRunner
from erk.cli.commands.implement import implement
runner = CliRunner()
result = runner.invoke(implement, ['-d', '--help'], catch_exceptions=False)
# -d should be accepted without error
"
```

And verify `-d` appears in help output:
```bash
uv run erk impl --help | grep -- '-d'
```

## Files NOT Changing

All files — no changes needed. The feature is fully implemented.