---
title: CLI Command Group Structure
read_when:
  - "creating a new command group"
  - "adding commands to an existing group"
  - "understanding command file organization"
last_audited: "2026-02-07 13:50 PT"
audit_result: edited
---

# CLI Command Group Structure

This document covers the **code structure** for Click command groups. For decisions about where to place commands (top-level vs grouped), see [Command Organization](command-organization.md).

## Directory Structure

```
src/erk/cli/commands/
├── [group-name]/
│   ├── __init__.py           # Group definition + subcommand registration
│   ├── [action]_cmd.py       # Individual commands (verb_cmd.py)
│   └── [subgroup]/           # Optional nested subgroups
└── [standalone].py           # Top-level commands (not in groups)
```

## Group Definition Pattern

The `__init__.py` defines the group and registers commands using `register_with_aliases`:

```python
"""Objective management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.objective.check_cmd import check_objective
from erk.cli.commands.objective.close_cmd import close_objective
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.help_formatter import ErkCommandGroup


@click.group("objective", cls=ErkCommandGroup)
def objective_group() -> None:
    """Manage objectives (multi-PR coordination issues)."""
    pass


register_with_aliases(objective_group, check_objective)
register_with_aliases(objective_group, close_objective)
register_with_aliases(objective_group, list_objectives)
```

Key details:

- Use `cls=ErkCommandGroup` in `@click.group()` for consistent help formatting
- Use `register_with_aliases()` (not `add_command()`) to support command aliases

## Naming Conventions

| Element           | Pattern         | Example                                       |
| ----------------- | --------------- | --------------------------------------------- |
| Group function    | `{noun}_group`  | `objective_group`, `plan_group`, `wt_group`   |
| Command files     | `{verb}_cmd.py` | `check_cmd.py`, `close_cmd.py`, `list_cmd.py` |
| Command functions | `{verb}_{noun}` | `check_objective`, `close_objective`          |

## Individual Command Pattern

Each command lives in its own `*_cmd.py` file:

```python
# src/erk/cli/commands/objective/check_cmd.py
"""Check command for verifying objective state."""

import click

from erk.core.context import ErkContext


@click.command()
@click.pass_obj
def check_objective(ctx: ErkContext) -> None:
    """Check objective status."""
    # Implementation...
```

## Registering Groups in CLI Entry Point

Groups are registered in `src/erk/cli/cli.py`:

```python
from erk.cli.commands.objective import objective_group

cli.add_command(objective_group)
```

## Examples in Codebase

| Group Type               | Location                          |
| ------------------------ | --------------------------------- |
| Simple group             | `src/erk/cli/commands/objective/` |
| Simple group             | `src/erk/cli/commands/plan/`      |
| Group with more commands | `src/erk/cli/commands/wt/`        |
| Complex group            | `src/erk/cli/commands/stack/`     |

## Adding a New Command to Existing Group

1. Create `src/erk/cli/commands/{group}/{verb}_cmd.py`
2. Import and register in `src/erk/cli/commands/{group}/__init__.py`
3. Add tests for the new command

## Creating a New Command Group

1. Create directory: `src/erk/cli/commands/{noun}/`
2. Create `__init__.py` with group definition (use `cls=ErkCommandGroup`, `register_with_aliases`)
3. Create command files: `{verb}_cmd.py`
4. Register group in `src/erk/cli/cli.py`
5. Add tests for the new commands

## Related Documentation

- [Command Organization](command-organization.md) - Where to place commands (top-level vs grouped)
- [CLI Output Styling](output-styling.md) - Output formatting guidelines
