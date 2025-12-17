"""Development tools command group."""

import click

from erk.cli.commands.dev.kit_check import kit_check


@click.group(name="dev")
def dev_group() -> None:
    """Development tools for kit authors.

    Commands for validating kit structure and checking for issues
    during kit development.
    """


# Register dev commands
dev_group.add_command(kit_check)
