"""Session commands for ccsesh CLI."""

from pathlib import Path

import click


def get_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def encode_path_to_project_id(path: Path) -> str:
    """Encode filesystem path to project folder name.

    Uses Claude Code's encoding: replace / with -
    Example: /Users/alice/code/myapp -> -Users-alice-code-myapp
    """
    return str(path.resolve()).replace("/", "-")


def resolve_project_dir(
    project_id: str | None,
    project_path: str | None,
    cwd: Path,
) -> Path | None:
    """Resolve project directory from options or current directory.

    Priority:
    1. --project-id: Use directly as folder name
    2. --project-path: Encode path to folder name
    3. Neither: Infer from current working directory

    Returns None if project directory doesn't exist.
    """
    projects_dir = get_projects_dir()

    if project_id:
        project_dir = projects_dir / project_id
    elif project_path:
        project_dir = projects_dir / encode_path_to_project_id(Path(project_path))
    else:
        project_dir = projects_dir / encode_path_to_project_id(cwd)

    if project_dir.exists():
        return project_dir
    return None


@click.group(name="session")
def session() -> None:
    """Manage Claude Code sessions."""
    pass


@session.command(name="list")
@click.option("--project-id", help="Project folder name (encoded)")
@click.option("--project-path", help="Filesystem path to project")
def list_sessions(project_id: str | None, project_path: str | None) -> None:
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

    # Find all session files (exclude agent-*.jsonl)
    session_files = [
        f
        for f in project_dir.iterdir()
        if f.is_file() and f.suffix == ".jsonl" and not f.name.startswith("agent-")
    ]

    # Sort by mtime, newest first
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    if not session_files:
        click.echo("No sessions found.")
        return

    for f in session_files:
        # Output session ID (filename without .jsonl extension)
        click.echo(f.stem)
