"""Project-related API functions for ccsesh."""

from functools import cache
from pathlib import Path


@cache
def get_projects_dir() -> Path:
    """Get the Claude Code projects directory (~/.claude/projects)."""
    return Path.home() / ".claude" / "projects"


def encode_path_to_project_id(path: Path) -> str:
    """Encode filesystem path to project folder name.

    Uses Claude Code's encoding: replace / with -
    Example: /Users/alice/code/myapp -> -Users-alice-code-myapp
    """
    return str(path.resolve()).replace("/", "-")


def list_projects(projects_dir: Path | None = None) -> list[Path]:
    """List all Claude Code project directories, sorted by mtime (newest first).

    Args:
        projects_dir: Override the projects directory (for testing).
                      If None, uses get_projects_dir().

    Returns:
        List of project directory paths, sorted by modification time (newest first).
        Returns empty list if projects directory doesn't exist.
    """
    if projects_dir is None:
        projects_dir = get_projects_dir()

    if not projects_dir.exists():
        return []

    return sorted(
        [d for d in projects_dir.iterdir() if d.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
