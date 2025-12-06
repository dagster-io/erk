"""Scratch space utilities for inter-process file passing.

Provides functions for writing temp files to `.erk/scratch/sessions/<session-id>/` in the repo root.
Each Claude session gets its own subdirectory, making debugging and auditing easier.

Directory structure:
    .erk/scratch/
        sessions/<session-id>/     # Session-scoped files (isolated per Claude session)
        <worktree-scoped files>    # Top-level for worktree-scoped scratch files
"""

import subprocess
import time
import uuid
from pathlib import Path


def _get_repo_root() -> Path:
    """Get the repository root via git rev-parse.

    Returns:
        Path to the git repository root.

    Raises:
        RuntimeError: If not in a git repository or git is not available.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return Path(result.stdout.strip())


def get_scratch_dir(
    session_id: str,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Get or create the .erk/scratch/sessions/<session_id>/ scratch directory.

    Args:
        session_id: Claude session ID for isolation.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        Path to .erk/scratch/sessions/<session_id>/ directory (creates if needed).
    """
    if repo_root is None:
        repo_root = _get_repo_root()

    scratch_dir = repo_root / ".erk" / "scratch" / "sessions" / session_id
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


def write_scratch_file(
    content: str,
    *,
    session_id: str,
    suffix: str = ".txt",
    prefix: str = "scratch-",
    repo_root: Path | None = None,
) -> Path:
    """Write content to a scratch file with unique name.

    Args:
        content: Content to write.
        session_id: Claude session ID for isolation.
        suffix: File extension (e.g., ".diff").
        prefix: Filename prefix for categorization.
        repo_root: Optional repo root (auto-detected if None).

    Returns:
        Path to the created file (e.g., .erk/scratch/sessions/<session_id>/diff-abc12345.diff).
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)

    # Generate unique filename using same pattern as tempfile
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{prefix}{unique_id}{suffix}"
    file_path = scratch_dir / filename

    file_path.write_text(content, encoding="utf-8")
    return file_path


def cleanup_stale_scratch(
    *,
    max_age_seconds: int = 3600,
    repo_root: Path | None = None,
) -> int:
    """Remove scratch session directories older than max_age_seconds.

    Removes entire session directories (not individual files) based on
    directory mtime. This cleans up after sessions that didn't clean up.

    Args:
        max_age_seconds: Maximum age in seconds before a directory is stale.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        Number of session directories cleaned up.
    """
    if repo_root is None:
        repo_root = _get_repo_root()

    sessions_dir = repo_root / ".erk" / "scratch" / "sessions"
    if not sessions_dir.exists():
        return 0

    cleaned = 0
    now = time.time()

    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue

        age = now - session_dir.stat().st_mtime
        if age > max_age_seconds:
            # Remove all files in the session directory
            for file_path in session_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            # Remove the empty directory
            session_dir.rmdir()
            cleaned += 1

    return cleaned
