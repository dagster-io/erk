"""Session discovery for extraction workflow.

This module provides functions to discover Claude Code sessions
in a project directory.
"""

from pathlib import Path

from erk_shared.extraction.types import BranchContext, SessionInfo
from erk_shared.git.abc import Git


def get_branch_context(git: Git, cwd: Path) -> BranchContext:
    """Get git branch context for determining session selection behavior.

    Args:
        git: Git interface for branch operations
        cwd: Current working directory

    Returns:
        BranchContext with current branch, trunk branch, and trunk status
    """
    current_branch = git.get_current_branch(cwd) or ""
    trunk_branch = git.detect_trunk_branch(cwd)

    return BranchContext(
        current_branch=current_branch,
        trunk_branch=trunk_branch,
        is_on_trunk=current_branch == trunk_branch,
    )


def discover_sessions(
    project_dir: Path,
    current_session_id: str | None,
    min_size: int = 0,
    limit: int = 10,
) -> list[SessionInfo]:
    """Discover sessions in project directory sorted by modification time.

    Args:
        project_dir: Path to Claude Code project directory
        current_session_id: Current session ID (for marking)
        min_size: Minimum session size in bytes (filters out tiny sessions)
        limit: Maximum number of sessions to return

    Returns:
        List of SessionInfo sorted by mtime descending (newest first)
    """
    sessions: list[SessionInfo] = []

    if not project_dir.exists():
        return sessions

    # Collect session files (exclude agent logs)
    session_files: list[tuple[Path, float, int]] = []
    for log_file in project_dir.iterdir():
        if not log_file.is_file():
            continue
        if log_file.suffix != ".jsonl":
            continue
        if log_file.name.startswith("agent-"):
            continue

        stat = log_file.stat()
        mtime = stat.st_mtime
        size = stat.st_size

        # Filter by minimum size
        if min_size > 0 and size < min_size:
            continue

        session_files.append((log_file, mtime, size))

    # Sort by mtime descending (newest first)
    session_files.sort(key=lambda x: x[1], reverse=True)

    # Take limit
    for log_file, mtime, size in session_files[:limit]:
        session_id = log_file.stem

        sessions.append(
            SessionInfo(
                session_id=session_id,
                path=log_file,
                size_bytes=size,
                mtime_unix=mtime,
                is_current=(session_id == current_session_id),
            )
        )

    return sessions


def encode_path_to_project_folder(path: Path) -> str:
    """Encode filesystem path to Claude Code project folder name.

    Claude Code uses a simple encoding scheme:
    - Replace "/" with "-"
    - Replace "." with "-"

    This creates deterministic folder names in ~/.claude/projects/.

    Args:
        path: Filesystem path to encode

    Returns:
        Encoded path suitable for project folder name

    Examples:
        >>> encode_path_to_project_folder(Path("/Users/foo/bar"))
        '-Users-foo-bar'
        >>> encode_path_to_project_folder(Path("/Users/foo/.config"))
        '-Users-foo--config'
    """
    return str(path).replace("/", "-").replace(".", "-")


def find_project_dir(cwd: Path) -> Path | None:
    """Find Claude Code project directory for a filesystem path.

    Args:
        cwd: Current working directory

    Returns:
        Path to project directory if found, None otherwise
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    # Encode path and find project directory
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = projects_dir / encoded_path

    if not project_dir.exists():
        return None

    return project_dir
