"""Worktree management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.status import status_cmd
from erk.cli.commands.wt.create_cmd import create_wt
from erk.cli.commands.wt.current_cmd import current_wt
from erk.cli.commands.wt.delete_cmd import delete_wt
from erk.cli.commands.wt.goto_cmd import goto_wt
from erk.cli.commands.wt.list_cmd import list_wt
from erk.cli.commands.wt.rename_cmd import rename_wt
from erk.cli.help_formatter import GroupedCommandGroup


@click.group("wt", cls=GroupedCommandGroup)
def wt_group() -> None:
    """Manage git worktrees."""
    pass


# Register subcommands
wt_group.add_command(create_wt)
wt_group.add_command(current_wt)
wt_group.add_command(delete_wt)
wt_group.add_command(goto_wt)
register_with_aliases(wt_group, list_wt)
wt_group.add_command(rename_wt)
wt_group.add_command(status_cmd)
