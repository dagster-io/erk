"""Project management commands."""

import click

from erk.cli.commands.project.init_cmd import init_project
from erk.cli.help_formatter import ErkCommandGroup


@click.group("project", cls=ErkCommandGroup, grouped=False)
def project_group() -> None:
    """Manage project or projects (within a monorepo)."""
    pass


# Register subcommands
project_group.add_command(init_project)
