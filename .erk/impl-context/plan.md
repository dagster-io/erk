# Plan: Add `erk stack restack` command

## Context

When `gt restack` encounters merge conflicts, the user must manually: (1) resolve conflicts, (2) launch Claude Code, (3) run `/erk:fix-conflicts`. This command automates that workflow — running `gt restack` and automatically launching Claude with `/erk:fix-conflicts` when conflicts are detected.

## Changes

### 1. New file: `src/erk/cli/commands/stack/restack_cmd.py`

Create a Click command `restack` using `cls=GraphiteCommand` (requires Graphite):

```python
@click.command("restack", cls=GraphiteCommand)
@click.pass_obj
def restack_stack(ctx: ErkContext) -> None:
```

Logic:
1. Run `gt restack --no-interactive` via subprocess (`check=False` LBYL pattern — not a wrapper since we need the exit code)
2. **If success** (returncode 0): print success message, exit
3. **If failure**: run `git status` and check for `"rebase in progress"` or `"Unmerged paths"` in output
   - **If conflicts detected**:
     - If `CLAUDECODE` env var is set (already inside Claude): print message suggesting `/erk:fix-conflicts` and `raise SystemExit(1)`
     - Otherwise: print "Conflicts detected, launching Claude..." and `os.execvp("claude", ["claude", "/erk:fix-conflicts"])` to replace process with interactive Claude session
   - **If other error**: print the gt error output and `raise SystemExit(1)`

### 2. Update: `src/erk/cli/commands/stack/__init__.py`

Import and register the new command:
```python
from erk.cli.commands.stack.restack_cmd import restack_stack
stack_group.add_command(restack_stack, name="restack")
```

## Key patterns followed

- `GraphiteCommand` class for automatic Graphite availability check (from `graphite_command.py`)
- LBYL subprocess pattern with `check=False` (per subprocess-wrappers.md — graceful degradation)
- `os.execvp` process replacement for launching Claude (same pattern as `execute_interactive_mode` in `implement_shared.py`)
- `CLAUDECODE` env var guard to avoid nested Claude sessions (per subprocess_utils.py docs)
- `--no-interactive` flag on all `gt` commands (per AGENTS.md critical rule)

## Files to modify

- `src/erk/cli/commands/stack/restack_cmd.py` (new)
- `src/erk/cli/commands/stack/__init__.py` (register command)

## Verification

- Run `erk stack restack --help` to verify command is registered
- Test on a branch that needs restacking with conflicts to verify Claude is launched
- Test on a clean stack to verify success path
- Test from within Claude Code to verify CLAUDECODE guard
