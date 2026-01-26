"""Workflow management commands."""

import click

from erk.cli.commands.workflow.launch_cmd import workflow_launch


@click.group("workflow")
def workflow_group() -> None:
    """Trigger GitHub Actions workflows."""
    pass


workflow_group.add_command(workflow_launch)
