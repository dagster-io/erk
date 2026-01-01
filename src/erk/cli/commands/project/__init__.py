"""Project management commands."""

import click

from erk.cli.commands.project.init_cmd import init_project
from erk.cli.commands.project.repo_init_cmd import repo_init_cmd
from erk.cli.commands.project.upgrade_cmd import upgrade_cmd
from erk.cli.help_formatter import ErkCommandGroup


@click.group("project", cls=ErkCommandGroup, grouped=False)
def project_group() -> None:
    """Manage project or projects (within a monorepo)."""
    pass


# Register subcommands
project_group.add_command(repo_init_cmd, name="init")
project_group.add_command(upgrade_cmd, name="upgrade")
project_group.add_command(init_project, name="subproject")
