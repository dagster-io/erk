"""Project commands for ccsesh CLI."""

import click

from ccsesh.api.projects import list_projects


@click.group(name="project")
def project() -> None:
    """Manage Claude Code projects."""
    pass


@project.command(name="list")
def list_projects_cmd() -> None:
    """List all Claude Code projects."""
    projects = list_projects()

    if not projects:
        click.echo("No projects found.")
        return

    for folder in projects:
        click.echo(folder.name)
