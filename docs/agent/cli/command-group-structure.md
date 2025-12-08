---
title: CLI Command Group Structure
read_when:
  - "creating new command groups"
  - "organizing Click commands"
  - "adding commands to existing groups"
  - "understanding command file structure"
---

# CLI Command Group Structure

This document describes the directory structure and patterns for organizing Click command groups in erk.

## Directory Structure

Command groups follow a consistent directory pattern:

```
src/erk/cli/commands/
├── [group-name]/
│   ├── __init__.py           # Group definition + subcommand registration
│   ├── [action]_cmd.py       # Individual commands (verb_cmd.py)
│   └── [subgroup]/           # Optional nested subgroups
└── [standalone].py           # Top-level commands (not in groups)
```

### Example: Simple Group

The `plan` group shows the basic pattern:

```
src/erk/cli/commands/plan/
├── __init__.py           # plan_group() definition
├── create_cmd.py         # create_plan() command
├── get_cmd.py            # get_plan() command
└── list_cmd.py           # list_plans() command
```

### Example: Complex Group with Subgroups

The `stack` group demonstrates nested structure:

```
src/erk/cli/commands/stack/
├── __init__.py           # stack_group() definition
├── submit_cmd.py         # submit_stack() command
├── sync_cmd.py           # sync_stack() command
└── pr/                   # Nested subgroup
    ├── __init__.py       # pr_subgroup() definition
    └── update_cmd.py     # update_pr() command
```

## Naming Conventions

### Group Function

The `__init__.py` defines the group with the pattern: `{noun}_group`

```python
import click

@click.group(name="objective")
def objective_group():
    """Commands for managing objectives."""
    pass
```

**Examples**:

- `objective_group` (noun: objective)
- `plan_group` (noun: plan)
- `worktree_group` (noun: worktree)

### Command Files

Individual command files follow: `{verb}_cmd.py`

```python
# turn_cmd.py
import click

@click.command(name="turn")
@click.pass_obj
def turn_objective(ctx):
    """Execute one objective evaluation turn."""
    pass
```

**Examples**:

- `create_cmd.py` - Creates a new resource
- `turn_cmd.py` - Executes a turn
- `list_cmd.py` - Lists resources
- `delete_cmd.py` - Deletes a resource

### Command Functions

Command functions follow: `{verb}_{noun}`

```python
# In turn_cmd.py
def turn_objective(ctx):  # verb_noun pattern
    pass

# In create_cmd.py
def create_objective(ctx):
    pass
```

## Group Registration Pattern

The `__init__.py` file handles two responsibilities:

1. **Define the group** using `@click.group()`
2. **Register commands** using `group.add_command()`

### Simple Registration

```python
# src/erk/cli/commands/objective/__init__.py
import click
from .create_cmd import create_objective
from .turn_cmd import turn_objective
from .list_cmd import list_objectives

@click.group(name="objective")
def objective_group():
    """Commands for managing long-running objectives."""
    pass

# Register commands
objective_group.add_command(create_objective)
objective_group.add_command(turn_objective)
objective_group.add_command(list_objectives)
```

### With Subgroups

```python
# src/erk/cli/commands/stack/__init__.py
import click
from .submit_cmd import submit_stack
from .pr.update_cmd import update_stack_pr

@click.group(name="stack")
def stack_group():
    """Commands for managing stacks."""
    pass

# Subgroup
@stack_group.group(name="pr")
def pr_subgroup():
    """PR operations for stacks."""
    pass

# Register to subgroup
pr_subgroup.add_command(update_stack_pr)
```

## Command Registration in Main CLI

After defining a group, register it in the main CLI entry point:

```python
# src/erk/cli/main.py
from erk.cli.commands.objective import objective_group

@click.group()
def cli():
    pass

cli.add_command(objective_group)
```

## File Locations

### Real Examples in Codebase

**Simple group**:

- Group definition: `src/erk/cli/commands/plan/__init__.py`
- Command: `src/erk/cli/commands/plan/create_cmd.py`

**Complex group with subgroups**:

- Group definition: `src/erk/cli/commands/stack/__init__.py`
- Subgroup: `src/erk/cli/commands/stack/pr/__init__.py`
- Subgroup command: `src/erk/cli/commands/stack/pr/update_cmd.py`

**Top-level command** (not in group):

- Single file: `src/erk/cli/commands/status.py`

## When to Group vs Top-Level

**Use a group when**:

- Multiple related commands share a noun (e.g., `objective create`, `objective turn`)
- Commands are infrastructure-level (e.g., `wt create`, `wt delete`)
- Namespace collision would occur at top-level

**Use top-level when**:

- Command is high-frequency and plan-oriented (e.g., `erk get`, `erk implement`)
- Command is unique and doesn't belong to a logical group (e.g., `erk status`)
- Minimizing keystrokes is important for ergonomics

**Related**: [CLI Command Organization](command-organization.md)

## Related Documentation

- [CLI Command Organization](command-organization.md) — command hierarchy philosophy
- [Erk Architecture Patterns](../architecture/erk-architecture.md) — context and dependency injection
