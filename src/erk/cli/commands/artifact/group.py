"""Artifact command group."""

import click

from erk.cli.commands.artifact.list import list_artifacts, ls
from erk.cli.commands.artifact.show import show_artifact


@click.group(name="artifact")
def artifact_group() -> None:
    """Manage and inspect Claude Code artifacts."""
    pass


# Register commands
artifact_group.add_command(list_artifacts)
artifact_group.add_command(ls)
artifact_group.add_command(show_artifact)
