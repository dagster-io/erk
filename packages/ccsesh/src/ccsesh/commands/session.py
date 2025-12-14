"""Session commands for ccsesh CLI."""

from pathlib import Path

import click

from ccsesh.api.sessions import list_sessions, resolve_project_dir


@click.group(name="session")
def session() -> None:
    """Manage Claude Code sessions."""
    pass


@session.command(name="list")
@click.option("--project-id", help="Project folder name (encoded)")
@click.option("--project-path", help="Filesystem path to project")
def list_sessions_cmd(project_id: str | None, project_path: str | None) -> None:
    """List sessions for a project.

    By default, uses the current directory to find the project.
    Use --project-id or --project-path to specify a different project.
    """
    project_dir = resolve_project_dir(project_id, project_path, Path.cwd())

    if project_dir is None:
        if project_id:
            click.echo(f"Project not found: {project_id}", err=True)
        elif project_path:
            click.echo(f"No project found for path: {project_path}", err=True)
        else:
            click.echo(f"No project found for current directory: {Path.cwd()}", err=True)
        raise SystemExit(1)

    sessions = list_sessions(project_dir)

    if not sessions:
        click.echo("No sessions found.")
        return

    for session_id in sessions:
        click.echo(session_id)
