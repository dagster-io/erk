"""Session discovery for extraction workflow.

This module provides functions to discover Claude Code sessions
in a project directory.
"""

from pathlib import Path

from erk_shared.extraction.session_environment import SessionEnvironment
from erk_shared.extraction.types import BranchContext, SessionInfo
from erk_shared.git.abc import Git


def get_current_session_id(env: SessionEnvironment) -> str | None:
    """Extract current session ID from SESSION_CONTEXT environment variable.

    The SESSION_CONTEXT env var contains: session_id=<uuid>

    Args:
        env: Session environment for accessing env vars

    Returns:
        Session ID string or None if not found
    """
    ctx = env.get_session_context_env() or ""
    if "session_id=" in ctx:
        return ctx.split("session_id=")[1].strip()
    return None


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
    env: SessionEnvironment,
    min_size: int = 0,
    limit: int = 10,
) -> list[SessionInfo]:
    """Discover sessions in project directory sorted by modification time.

    Args:
        project_dir: Path to Claude Code project directory
        current_session_id: Current session ID (for marking)
        env: Session environment for filesystem operations
        min_size: Minimum session size in bytes (filters out tiny sessions)
        limit: Maximum number of sessions to return

    Returns:
        List of SessionInfo sorted by mtime descending (newest first)
    """
    sessions: list[SessionInfo] = []

    if not env.path_exists(project_dir):
        return sessions

    # Collect session files (exclude agent logs)
    session_files: list[tuple[Path, float, int]] = []
    for log_file in env.list_directory(project_dir):
        if not env.is_file(log_file):
            continue
        if log_file.suffix != ".jsonl":
            continue
        if log_file.name.startswith("agent-"):
            continue

        mtime, size = env.get_file_stat(log_file)

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


def find_project_dir(cwd: Path, env: SessionEnvironment) -> Path | None:
    """Find Claude Code project directory for a filesystem path.

    Args:
        cwd: Current working directory
        env: Session environment for filesystem operations

    Returns:
        Path to project directory if found, None otherwise
    """
    projects_dir = env.get_home_dir() / ".claude" / "projects"
    if not env.path_exists(projects_dir):
        return None

    # Encode path and find project directory
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = projects_dir / encoded_path

    if not env.path_exists(project_dir):
        return None

    return project_dir
