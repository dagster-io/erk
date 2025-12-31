"""Artifact command group for managing .claude/ artifacts."""

import click

from erk.cli.commands.artifact.check import check_cmd
from erk.cli.commands.artifact.list_cmd import list_cmd
from erk.cli.commands.artifact.show import show_cmd
from erk.cli.commands.artifact.sync_cmd import sync_cmd


@click.group(name="artifact")
def artifact_group() -> None:
    """Manage erk-managed artifacts.

    Artifacts are Claude Code extensions like skills, commands, agents,
    and workflows stored in your project's .claude/ and .github/ directories.

    \b
    Commands:
      list   List installed artifacts
      show   Display artifact content
      sync   Sync artifacts from erk package
      check  Check if artifacts are up to date
    """


# Register subcommands
artifact_group.add_command(list_cmd)
artifact_group.add_command(show_cmd)
artifact_group.add_command(sync_cmd)
artifact_group.add_command(check_cmd)
