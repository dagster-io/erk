"""Artifacts command group for sync operations."""

import click

from erk.cli.commands.artifacts.check import check
from erk.cli.commands.artifacts.sync import sync


@click.group()
def artifacts() -> None:
    """Manage erk artifact synchronization."""
    pass


artifacts.add_command(sync)
artifacts.add_command(check)
