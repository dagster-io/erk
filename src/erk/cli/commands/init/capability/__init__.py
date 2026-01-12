"""Capability management subcommands for erk init."""

import click

from erk.cli.commands.init.capability.add_cmd import add_cmd
from erk.cli.commands.init.capability.check_cmd import check_cmd
from erk.cli.commands.init.capability.list_cmd import list_cmd
from erk.cli.commands.init.capability.remove_cmd import remove_cmd
from erk.cli.help_formatter import ErkCommandGroup


@click.group("capability", cls=ErkCommandGroup)
def capability_group() -> None:
    """Manage optional erk capabilities.

    Capabilities are optional features that can be installed in a repository.
    Use these commands to list, check, add, and remove capabilities.
    """
    pass


# Register subcommands
capability_group.add_command(list_cmd)
capability_group.add_command(check_cmd)
capability_group.add_command(add_cmd)
capability_group.add_command(remove_cmd)
