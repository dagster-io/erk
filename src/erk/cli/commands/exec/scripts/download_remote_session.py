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
from collections.abc import Callable
from pathlib import Path

import click

from erk_shared.context.helpers import require_repo_root


def normalize_gist_url(gist_url: str) -> str:
    """Convert gist webpage URL to raw content URL if needed.

    Accepts:
    - gist.github.com/user/id -> converts to raw URL
    - gist.githubusercontent.com/user/id/raw/file -> uses as-is

    Args:
        gist_url: Gist URL (either webpage or raw).

    Returns:
        Raw gist URL that can be used with urlopen.
    """
    # If URL already points to raw content, use as-is
    if "gist.githubusercontent.com" in gist_url:
        return gist_url

    # Convert webpage URL to raw URL
    # Use /raw/ without filename - GitHub redirects to the first file in single-file gists
    if "gist.github.com" in gist_url:
        normalized = gist_url.replace("gist.github.com", "gist.githubusercontent.com").rstrip("/")
        return f"{normalized}/raw/"

    # Unknown format, return as-is and let urlopen handle it
    return gist_url


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


def _real_url_fetch(url: str) -> bytes:
    """Production URL fetcher using urllib."""
    with urllib.request.urlopen(url) as response:
        return response.read()


def _download_from_gist(
    gist_url: str,
    session_dir: Path,
    *,
    url_fetcher: Callable[[str], bytes],
) -> Path | str:
    """Download session content from a gist URL.

    Handles both webpage URLs (gist.github.com) and raw URLs (gist.githubusercontent.com).

    Args:
        gist_url: Gist URL (webpage or raw).
        session_dir: Directory to save the session file in.
        url_fetcher: Callable that fetches URL content as bytes.

    Returns:
        Path to the downloaded session file on success, error message string on failure.
    """
    normalized_url = normalize_gist_url(gist_url)
    try:
        content = url_fetcher(normalized_url)
        session_file = session_dir / "session.jsonl"
        session_file.write_bytes(content)
        return session_file
    except urllib.error.URLError as e:
        return f"Failed to download from gist URL: {e}"


def _execute_download(
    *,
    repo_root: Path,
    gist_url: str,
    session_id: str,
    url_fetcher: Callable[[str], bytes],
) -> tuple[int, dict[str, object]]:
    """Core download logic.

    Args:
        repo_root: Repository root path.
        gist_url: Gist URL (webpage or raw).
        session_id: Claude session ID.
        url_fetcher: Callable that fetches URL content as bytes.

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

    result = _download_from_gist(gist_url, session_dir, url_fetcher=url_fetcher)
    if isinstance(result, str):
        return 1, {"success": False, "error": result}

    return 0, {
        "success": True,
        "session_id": session_id,
        "path": str(result),
        "source": "gist",
    }


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
    exit_code, output = _execute_download(
        repo_root=repo_root,
        gist_url=gist_url,
        session_id=session_id,
        url_fetcher=_real_url_fetch,
    )
    click.echo(json.dumps(output))
    if exit_code != 0:
        raise SystemExit(exit_code)
