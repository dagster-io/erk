"""Planner box management commands."""

import click

from erk.cli.commands.planner.configure_cmd import configure_planner
from erk.cli.commands.planner.connect_cmd import connect_planner
from erk.cli.commands.planner.create_cmd import create_planner
from erk.cli.commands.planner.list_cmd import list_planners
from erk.cli.commands.planner.register_cmd import register_planner
from erk.cli.commands.planner.set_default_cmd import set_default_planner
from erk.cli.commands.planner.unregister_cmd import unregister_planner
from erk.cli.help_formatter import GroupedCommandGroup


@click.group("planner", cls=GroupedCommandGroup, invoke_without_command=True)
@click.pass_context
def planner_group(ctx: click.Context) -> None:
    """Manage planner boxes (GitHub Codespaces for remote planning).

    A planner box is a GitHub Codespace pre-configured for remote planning
    with Claude Code. Use 'erk planner register' to register an existing
    codespace, then 'erk planner' to connect.

    When invoked without a subcommand, connects to the default planner.
    """
    # If no subcommand provided, invoke connect to default
    if ctx.invoked_subcommand is None:
        ctx.invoke(connect_planner)


# Register subcommands
planner_group.add_command(connect_planner)
planner_group.add_command(create_planner)
planner_group.add_command(configure_planner)
planner_group.add_command(register_planner)
planner_group.add_command(unregister_planner)
planner_group.add_command(list_planners)
planner_group.add_command(set_default_planner)
