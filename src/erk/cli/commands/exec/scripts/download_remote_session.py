"""Download a Claude Code session from a GitHub Gist URL.

This exec command downloads a session and stores it in the
.erk/scratch/remote-sessions/ directory for learn workflow processing.

Usage:
    erk exec download-remote-session --gist-url <gist-raw-url> --session-id abc-123

Output:
    Structured JSON output with success status and session file path

Exit Codes:
    0: Success (session file downloaded and located)
    1: Error (download failed)

Examples:
    $ erk exec download-remote-session --gist-url <gist-raw-url> --session-id abc-123
    {
      "success": true,
      "session_id": "abc-123",
      "path": "...",
      "source": "gist"
    }
"""

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import click

from erk_shared.context.helpers import require_repo_root


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


def _download_from_gist(gist_url: str, session_dir: Path) -> Path | str:
    """Download session content from a gist raw URL.

    Args:
        gist_url: Raw gist URL to download from.
        session_dir: Directory to save the session file in.

    Returns:
        Path to the downloaded session file on success, error message string on failure.
    """
    try:
        with urllib.request.urlopen(gist_url) as response:
            content = response.read()
        session_file = session_dir / "session.jsonl"
        session_file.write_bytes(content)
        return session_file
    except urllib.error.URLError as e:
        return f"Failed to download from gist URL: {e}"


@click.command(name="download-remote-session")
@click.option(
    "--gist-url",
    required=True,
    help="Raw gist URL to download session from",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID (used to name output directory)",
)
@click.pass_context
def download_remote_session(
    ctx: click.Context,
    gist_url: str,
    session_id: str,
) -> None:
    """Download a session from a GitHub Gist.

    Downloads the session JSONL from the provided gist raw URL and stores it
    in .erk/scratch/remote-sessions/{session_id}/.

    The command:
    1. Cleans up existing directory if present (idempotent)
    2. Downloads session from gist
    3. Returns path to the session file
    """
    repo_root = require_repo_root(ctx)

    # Get or create the remote sessions directory
    session_dir = _get_remote_sessions_dir(repo_root, session_id)

    # Clean up existing directory contents for idempotent re-downloads
    if session_dir.exists():
        for item in session_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    # Download from gist
    result = _download_from_gist(gist_url, session_dir)
    if isinstance(result, str):
        # Error case - result is error message
        error_output = {
            "success": False,
            "error": result,
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Success case
    output: dict[str, object] = {
        "success": True,
        "session_id": session_id,
        "path": str(result),
        "source": "gist",
    }
    click.echo(json.dumps(output))
