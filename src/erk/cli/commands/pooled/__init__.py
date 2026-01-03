"""Pooled branch management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pooled.assign_cmd import pooled_assign
from erk.cli.commands.pooled.create_cmd import pooled_create
from erk.cli.commands.pooled.list_cmd import pooled_list
from erk.cli.commands.pooled.unassign_cmd import pooled_unassign
from erk.cli.help_formatter import ErkCommandGroup


@click.group("pooled", cls=ErkCommandGroup, grouped=False)
def pooled_group() -> None:
    """Manage pooled branches."""
    pass


# Register subcommands
pooled_group.add_command(pooled_create)
pooled_group.add_command(pooled_assign)
pooled_group.add_command(pooled_unassign)
register_with_aliases(pooled_group, pooled_list)
