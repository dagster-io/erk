"""Session commands for ccsesh CLI."""

from pathlib import Path

import click

from ccsesh.api.sessions import get_project_dir_by_id, get_project_dir_by_path, list_sessions
from ccsesh.cli import CcseshContext, pass_context


@click.group(name="session")
def session() -> None:
    """Manage Claude Code sessions."""
    pass


@session.command(name="list")
@click.option("--project-id", help="Project folder name (encoded)")
@click.option("--project-path", help="Filesystem path to project (absolute or relative)")
@pass_context
def list_sessions_cmd(ctx: CcseshContext, project_id: str | None, project_path: str | None) -> None:
    """List sessions for a project.

    By default, uses the current directory to find the project.
    Use --project-id or --project-path to specify a different project.
    """
    if project_id and project_path:
        click.echo("Error: --project-id and --project-path are mutually exclusive", err=True)
        raise SystemExit(1)

    if project_id:
        project_dir = get_project_dir_by_id(project_id)
        if project_dir is None:
            click.echo(f"Project not found: {project_id}", err=True)
            raise SystemExit(1)
    elif project_path:
        # Resolve relative paths to absolute (relative to ctx.cwd)
        path = Path(project_path)
        resolved_path = path if path.is_absolute() else (ctx.cwd / path).resolve()
        project_dir = get_project_dir_by_path(resolved_path)
        if project_dir is None:
            click.echo(f"No project found for path: {project_path}", err=True)
            raise SystemExit(1)
    else:
        project_dir = get_project_dir_by_path(ctx.cwd)
        if project_dir is None:
            click.echo(f"No project found for current directory: {ctx.cwd}", err=True)
            raise SystemExit(1)

    sessions = list_sessions(project_dir)

    if not sessions:
        click.echo("No sessions found.")
        return

    for session_id in sessions:
        click.echo(session_id)
