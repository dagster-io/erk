"""Worktree slot management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.slots.list_cmd import slots_list
from erk.cli.help_formatter import ErkCommandGroup


@click.group("slots", cls=ErkCommandGroup, grouped=False)
def slots_group() -> None:
    """Manage worktree slots."""
    pass


# Register subcommands
register_with_aliases(slots_group, slots_list)
