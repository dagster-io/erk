"""Session-related API functions for ccsesh."""

from pathlib import Path

from ccsesh.api.projects import encode_path_to_project_id, get_projects_dir


def get_project_dir_by_id(
    project_id: str,
    projects_dir: Path | None = None,
) -> Path | None:
    """Get project directory by encoded project ID.

    Args:
        project_id: Direct project folder name (encoded).
        projects_dir: Override the projects directory (for testing).
                      If None, uses get_projects_dir().

    Returns:
        Path to project directory, or None if it doesn't exist.
    """
    if projects_dir is None:
        projects_dir = get_projects_dir()

    project_dir = projects_dir / project_id
    if project_dir.exists():
        return project_dir
    return None


def get_project_dir_by_path(
    project_path: Path,
    projects_dir: Path | None = None,
) -> Path | None:
    """Get project directory by filesystem path.

    The path is encoded to a project ID and looked up.

    Args:
        project_path: Absolute filesystem path to project root.
        projects_dir: Override the projects directory (for testing).
                      If None, uses get_projects_dir().

    Returns:
        Path to project directory, or None if it doesn't exist.
    """
    if projects_dir is None:
        projects_dir = get_projects_dir()

    project_dir = projects_dir / encode_path_to_project_id(project_path)
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
