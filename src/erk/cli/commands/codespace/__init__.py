"""Codespace management commands."""

import click

from erk.cli.commands.codespace.connect_cmd import connect_codespace
from erk.cli.commands.codespace.list_cmd import list_codespaces
from erk.cli.commands.codespace.remove_cmd import remove_codespace
from erk.cli.commands.codespace.set_default_cmd import set_default_codespace_cmd
from erk.cli.commands.codespace.setup_cmd import setup_codespace
from erk.cli.help_formatter import ErkCommandGroup


@click.group("codespace", cls=ErkCommandGroup, grouped=False, hidden=True)
def codespace_group() -> None:
    """Manage codespaces for remote Claude execution.

    A codespace is a GitHub Codespace that can be used for running
    Claude Code remotely with full permissions (--dangerously-skip-permissions).

    Use 'erk codespace setup' to create and register a new codespace,
    then 'erk codespace connect' to connect.
    """


# Register subcommands
codespace_group.add_command(connect_codespace)
codespace_group.add_command(list_codespaces)
codespace_group.add_command(remove_codespace)
codespace_group.add_command(set_default_codespace_cmd)
codespace_group.add_command(setup_codespace)
