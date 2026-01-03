"""Pool management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pool.assign_cmd import pool_assign
from erk.cli.commands.pool.list_cmd import pool_list
from erk.cli.help_formatter import ErkCommandGroup


@click.group("pool", cls=ErkCommandGroup, grouped=False)
def pool_group() -> None:
    """Manage worktree pool."""
    pass


# Register subcommands
pool_group.add_command(pool_assign)
register_with_aliases(pool_group, pool_list)
