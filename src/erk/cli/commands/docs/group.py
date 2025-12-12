"""Agent documentation command group."""

import click

from erk.cli.commands.docs.init import init_command
from erk.cli.commands.docs.sync import sync_command
from erk.cli.commands.docs.validate import validate_command


@click.group(name="docs")
def docs_group() -> None:
    """Manage and validate agent documentation."""


# Register commands
docs_group.add_command(init_command)
docs_group.add_command(sync_command)
docs_group.add_command(validate_command)
