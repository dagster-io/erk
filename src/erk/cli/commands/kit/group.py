"""Kit commands group."""

import click

from erk.cli.commands.kit import install
from erk.cli.commands.kit.check import check
from erk.cli.commands.kit_exec.group import kit_exec_group


@click.group()
def kit_group() -> None:
    """Manage kits - install, update, and configure.

    Common commands:
      install    Install or update a specific kit
      exec       Execute scripts from bundled kits
    """


# Register all kit commands
kit_group.add_command(check)
kit_group.add_command(install.install)
kit_group.add_command(kit_exec_group, name="exec")
