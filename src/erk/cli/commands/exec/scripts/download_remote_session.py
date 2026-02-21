"""Download a Claude Code session from a git branch.

This exec command downloads a session and stores it in the
.erk/scratch/remote-sessions/ directory for learn workflow processing.

Usage:
    erk exec download-remote-session --session-branch session/123 --session-id abc-123

Output:
    Structured JSON output with success status and session file path

Exit Codes:
    0: Success (session file downloaded and located)
    1: Error (download failed)

Examples:
    $ erk exec download-remote-session --session-branch session/123 --session-id abc-123
    {
      "success": true,
      "session_id": "abc-123",
      "path": "...",
      "source": "branch"
    }
"""

import json
import shutil
import subprocess
from pathlib import Path

import click

from erk_shared.context.helpers import require_git, require_repo_root


def _get_remote_sessions_dir(repo_root: Path, session_id: str) -> Path:
    """Get the remote sessions directory for a session ID.

    Creates the directory if it doesn't exist.

    Args:
        repo_root: Repository root path.
        session_id: Session ID for the remote session.

    Returns:
        Path to .erk/scratch/remote-sessions/<session_id>/
    """
    remote_sessions_dir = repo_root / ".erk" / "scratch" / "remote-sessions" / session_id
    remote_sessions_dir.mkdir(parents=True, exist_ok=True)
    return remote_sessions_dir


def _download_from_branch(
    *,
    repo_root: Path,
    session_branch: str,
    session_id: str,
    session_dir: Path,
    git,
) -> Path | str:
    """Download session content from a git branch.

    Fetches the branch from origin and extracts the session JSONL via git show.

    Args:
        repo_root: Repository root path.
        session_branch: Branch name containing the session.
        session_id: Session ID used to locate the file on the branch.
        session_dir: Directory to save the session file in.
        git: Git gateway for remote operations.

    Returns:
        Path to the downloaded session file on success, error message string on failure.
    """
    git.remote.fetch_branch(repo_root, "origin", session_branch)

    session_file = session_dir / "session.jsonl"
    result = subprocess.run(
        ["git", "show", f"origin/{session_branch}:.erk/session/{session_id}.jsonl"],
        cwd=str(repo_root),
        capture_output=True,
    )
    if result.returncode != 0:
        return f"Failed to extract session from branch: {result.stderr.decode().strip()}"

    session_file.write_bytes(result.stdout)
    return session_file


def _execute_download(
    *,
    repo_root: Path,
    session_branch: str,
    session_id: str,
    git,
) -> tuple[int, dict[str, object]]:
    """Core download logic.

    Args:
        repo_root: Repository root path.
        session_branch: Branch name containing the session.
        session_id: Claude session ID.
        git: Git gateway for remote operations.

    Returns:
        Tuple of (exit_code, output_dict).
    """
    session_dir = _get_remote_sessions_dir(repo_root, session_id)

    # Clean up existing directory contents for idempotent re-downloads
    if session_dir.exists():
        for item in session_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    result = _download_from_branch(
        repo_root=repo_root,
        session_branch=session_branch,
        session_id=session_id,
        session_dir=session_dir,
        git=git,
    )
    if isinstance(result, str):
        return 1, {"success": False, "error": result}

    return 0, {
        "success": True,
        "session_id": session_id,
        "path": str(result),
        "source": "branch",
    }


@click.command(name="download-remote-session")
@click.option(
    "--session-branch",
    required=True,
    help="Git branch containing the session (e.g., session/123)",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID (used to locate file on the branch)",
)
@click.pass_context
def download_remote_session(
    ctx: click.Context,
    session_branch: str,
    session_id: str,
) -> None:
    """Download a session from a git branch.

    Fetches the session JSONL from the provided branch and stores it
    in .erk/scratch/remote-sessions/{session_id}/.

    The command:
    1. Cleans up existing directory if present (idempotent)
    2. Fetches the branch from origin
    3. Extracts the session JSONL via git show
    4. Returns path to the session file
    """
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    exit_code, output = _execute_download(
        repo_root=repo_root,
        session_branch=session_branch,
        session_id=session_id,
        git=git,
    )
    click.echo(json.dumps(output))
    if exit_code != 0:
        raise SystemExit(exit_code)
