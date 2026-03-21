---
title: --script Flag Behavior
read_when:
  - "implementing a command that supports --script mode"
  - "debugging cmux integration with shell activation scripts"
  - "understanding how --script interacts with --dry-run"
tripwires:
  - action: "combining --script and --dry-run on the same command invocation"
    warning: "--dry-run forces script=False. Dry-run produces human-readable output, not shell activation scripts. This is intentional: mixing the two modes would produce unusable output."
  - action: "adding --script as a visible option"
    warning: "--script is a hidden option (visible only when show_hidden_commands=True). Use the script_option decorator from src/erk/cli/help_formatter.py, not a manual click.option()."
---

# --script Flag Behavior

## What --script Does

The `--script` flag makes a command emit a shell activation script rather than normal output. The script is designed to be sourced by the shell, enabling the shell to cd, set environment variables, and execute post-cd commands.

Primary use case: cmux integration, where the terminal multiplexer sources the activation script to navigate to a new worktree.

## Hidden Option

`--script` is hidden by default. Visible only when `show_hidden_commands=True` in config:

```python
# src/erk/cli/help_formatter.py:80-97
def script_option(fn: F) -> F:
    """Adds --script option; hidden by default, visible with show_hidden_commands=True."""
    return click.option(
        "--script",
        is_flag=True,
        hidden=True,
        help="Output shell script for integration. NOT a dry run.",
    )(fn)
```

All commands that support `--script` use the `@script_option` decorator.

## Interaction with --dry-run

`--dry-run` takes precedence and forces `script=False`:

```python
# packages/erk-slots/src/erk_slots/teleport_cmd.py:114-116
# Dry-run forces human-readable output (no script mode)
if dry_run:
    script = False
```

The two modes are mutually exclusive:

- `--script`: Machine-readable shell activation output
- `--dry-run`: Human-readable preview of what would happen

## Use Cases

| Scenario                            | Flag        |
| ----------------------------------- | ----------- |
| cmux workspace navigation           | `--script`  |
| Non-interactive shell setup         | `--script`  |
| Preview operations before executing | `--dry-run` |
| Normal interactive use              | (neither)   |

## Related Documentation

- [Action Plan Pattern](../architecture/action-plan-pattern.md) — Dry-run support pattern used by teleport
- [erk_slots Package Overview](../erk/erk-slots-package.md) — Commands that use --script
