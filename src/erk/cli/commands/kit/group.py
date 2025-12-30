"""Kit commands group."""

import click

from erk.cli.commands.kit import install
from erk.cli.commands.kit.check import check


@click.group()
def kit_group() -> None:
    """Manage kits - install, update, and configure.

    Common commands:
      install    Install or update a specific kit
    """


# Register all kit commands
kit_group.add_command(check)
kit_group.add_command(install.install)
