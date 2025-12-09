"""Stack operation commands for managing worktree stacks."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.stack.consolidate_cmd import consolidate_stack
from erk.cli.commands.stack.list_cmd import list_stack
from erk.cli.commands.stack.move_cmd import move_stack
from erk.cli.commands.stack.split_old.command import split_cmd as split_stack


@click.group("stack")
def stack_group() -> None:
    """Manage worktree stack operations."""
    pass


# Register subcommands
stack_group.add_command(consolidate_stack, name="consolidate")
register_with_aliases(stack_group, list_stack, name="list")
stack_group.add_command(move_stack, name="move")
stack_group.add_command(split_stack, name="split")
