"""Codespace management commands."""

import click

from erk.cli.commands.codespace.connect_cmd import connect_codespace
from erk.cli.commands.codespace.setup_cmd import setup_codespace
from erk.cli.help_formatter import ErkCommandGroup


@click.group(
    "codespace", cls=ErkCommandGroup, grouped=False, invoke_without_command=True, hidden=True
)
@click.pass_context
def codespace_group(ctx: click.Context) -> None:
    """Manage codespaces for remote Claude execution.

    A codespace is a GitHub Codespace that can be used for running
    Claude Code remotely with full permissions (--dangerously-skip-permissions).

    Use 'erk codespace setup' to create and register a new codespace,
    then 'erk codespace' to connect.

    When invoked without a subcommand, connects to the default codespace.
    """
    # If no subcommand provided, invoke connect to default
    if ctx.invoked_subcommand is None:
        ctx.invoke(connect_codespace, name=None)


# Register subcommands
codespace_group.add_command(connect_codespace)
codespace_group.add_command(setup_codespace)
