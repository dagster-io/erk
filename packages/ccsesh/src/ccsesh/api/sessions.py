"""Session-related API functions for ccsesh."""

from pathlib import Path

from ccsesh.api.projects import encode_path_to_project_id, get_projects_dir


def resolve_project_dir(
    project_id: str | None,
    project_path: str | None,
    cwd: Path,
    projects_dir: Path | None = None,
) -> Path | None:
    """Resolve project directory from options or current directory.

    Priority:
    1. --project-id: Use directly as folder name
    2. --project-path: Encode path to folder name
    3. Neither: Infer from current working directory

    Args:
        project_id: Direct project folder name (encoded).
        project_path: Filesystem path to project root.
        cwd: Current working directory (fallback).
        projects_dir: Override the projects directory (for testing).
                      If None, uses get_projects_dir().

    Returns:
        Path to project directory, or None if it doesn't exist.
    """
    if projects_dir is None:
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


def list_sessions(project_dir: Path) -> list[str]:
    """List session IDs in a project directory, sorted by mtime (newest first).

    Excludes agent-*.jsonl files and non-.jsonl files.

    Args:
        project_dir: Path to the project directory.

    Returns:
        List of session IDs (filename stems), sorted by modification time (newest first).
    """
    session_files = [
        f
        for f in project_dir.iterdir()
        if f.is_file() and f.suffix == ".jsonl" and not f.name.startswith("agent-")
    ]

    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return [f.stem for f in session_files]
