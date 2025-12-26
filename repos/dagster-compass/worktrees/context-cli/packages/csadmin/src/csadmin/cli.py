"""CLI module for the Compass System Administration tool."""

import click
from csbot.ctx_admin.cli.migration_commands import migration

from csadmin.commands.check import check
from csadmin.commands.context import context
from csadmin.commands.init import init


@click.group()
@click.version_option()
def cli() -> None:
    """Compass System Administration CLI.

    This tool provides administrative utilities for managing
    the Compass system infrastructure and configuration.
    """
    pass


# Register commands
cli.add_command(check)
cli.add_command(init)
cli.add_command(context)
cli.add_command(migration.commands["migrate"])


if __name__ == "__main__":
    cli()
