"""Project commands for ccsesh CLI."""

from pathlib import Path

import click


def get_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


@click.group(name="project")
def project() -> None:
    """Manage Claude Code projects."""
    pass


@project.command(name="list")
def list_projects() -> None:
    """List all Claude Code projects."""
    projects_dir = get_projects_dir()

    if not projects_dir.exists():
        click.echo(f"No projects directory found at {projects_dir}")
        return

    project_folders = sorted(
        [d for d in projects_dir.iterdir() if d.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not project_folders:
        click.echo("No projects found.")
        return

    for folder in project_folders:
        click.echo(folder.name)
