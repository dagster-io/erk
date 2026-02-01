---
title: CLI Command Group Structure
read_when:
  - "creating a new command group"
  - "adding commands to an existing group"
  - "understanding command file organization"
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

The `__init__.py` defines the group and registers commands:

```python
"""Objective command group for managing long-running goals."""

import click

from erk.cli.commands.objective.get_cmd import get_objective
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.commands.objective.turn_cmd import turn_objective


@click.group("objective")
def objective_group() -> None:
    """Manage objectives."""
    pass


objective_group.add_command(list_objectives, name="list")
objective_group.add_command(get_objective, name="get")
objective_group.add_command(turn_objective, name="turn")
```

## Naming Conventions

| Element           | Pattern         | Example                                       |
| ----------------- | --------------- | --------------------------------------------- |
| Group function    | `{noun}_group`  | `objective_group`, `plan_group`, `wt_group`   |
| Command files     | `{verb}_cmd.py` | `create_cmd.py`, `turn_cmd.py`, `list_cmd.py` |
| Command functions | `{verb}_{noun}` | `create_objective`, `turn_objective`          |

## Individual Command Pattern

Each command lives in its own `*_cmd.py` file:

```python
# src/erk/cli/commands/objective/turn_cmd.py
"""Turn command for evaluating objectives."""

import click

from erk.core.context import ErkContext


@click.command()
@click.argument("objective_name")
@click.pass_obj
def turn_objective(ctx: ErkContext, objective_name: str) -> None:
    """Run a turn to evaluate objective state and generate plans."""
    # Implementation...
```

## Registering Groups in CLI Entry Point

Groups are registered in `src/erk/cli/cli.py`:

```python
from erk.cli.commands.objective import objective_group

cli.add_command(objective_group, name="objective")
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
3. Add test in `tests/commands/{group}/test_{verb}.py`

### Example: Extending `erk codespace run` Group

The `erk codespace run` group was extended in PR #6408 to add `erk codespace run objective next-plan`:

**Existing group structure:**

```
src/erk/cli/commands/codespace/
├── __init__.py                     # Codespace group
├── connect_cmd.py
├── setup_cmd.py
└── run/
    ├── __init__.py                 # Run subgroup
    └── next_plan_cmd.py            # NEW: objective next-plan subcommand
```

**Step 1: Create command file**

Create `src/erk/cli/commands/codespace/run/next_plan_cmd.py`:

```python
"""erk codespace run objective next-plan implementation."""

import click
from erk.cli.context import get_command_context
from erk.cli.commands.codespace.helpers import resolve_codespace
from erk.core.codespace_run import build_codespace_run_command


@click.command()
@click.argument("issue_ref")
@click.option("--codespace", "-c", help="Codespace name")
@click.pass_context
def next_plan_cmd(ctx: click.Context, issue_ref: str, codespace: str | None) -> None:
    """Execute 'erk objective next-plan' on a remote codespace."""
    cmd_ctx = get_command_context(ctx)
    cs = resolve_codespace(cmd_ctx.codespace_registry, codespace)
    cmd_ctx.codespace.start_codespace(cs.gh_name)
    remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")
    exit_code = cmd_ctx.codespace.run_ssh_command(cs.gh_name, remote_cmd)
    # ... handle exit code ...
```

**Step 2: Register in parent group**

In `src/erk/cli/commands/codespace/run/__init__.py`:

```python
"""Codespace run subcommands."""

import click
from erk.cli.commands.codespace.run.next_plan_cmd import next_plan_cmd


@click.group("run")
def run_group() -> None:
    """Run commands on codespaces."""
    pass


# Register subcommands
run_group.add_command(next_plan_cmd, name="objective")
```

**Step 3: Link to parent group**

In `src/erk/cli/commands/codespace/__init__.py`:

```python
from erk.cli.commands.codespace.run import run_group

codespace_group.add_command(run_group, name="run")
```

This creates the command chain: `erk codespace run objective next-plan`

**Step 4: Add tests**

Create `tests/unit/cli/commands/codespace/run/test_next_plan_cmd.py`:

```python
def test_starts_codespace_before_execution() -> None:
    """Verify codespace is started before SSH command."""
    # ... test implementation ...

def test_uses_default_codespace_when_not_specified() -> None:
    """Verify default codespace resolution."""
    # ... test implementation ...
```

## Creating a New Command Group

1. Create directory: `src/erk/cli/commands/{noun}/`
2. Create `__init__.py` with group definition
3. Create command files: `{verb}_cmd.py`
4. Register group in `src/erk/cli/cli.py`
5. Create test directory: `tests/commands/{noun}/`

## Related Documentation

- [Command Organization](command-organization.md) - Where to place commands (top-level vs grouped)
- [CLI Output Styling](output-styling.md) - Output formatting guidelines
