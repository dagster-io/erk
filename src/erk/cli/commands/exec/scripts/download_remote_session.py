"""Download a Claude Code session from a GitHub Actions artifact or Gist URL.

This exec command downloads a session and stores it in the
.erk/scratch/remote-sessions/ directory for learn workflow processing.

Supports two modes:
- Artifact mode: Download from GitHub Actions artifact (legacy)
- Gist mode: Download from GitHub Gist URL (preferred)

Usage:
    # From Gist URL (preferred)
    erk exec download-remote-session --gist-url <gist-raw-url> --session-id abc-123

    # From artifact (legacy)
    erk exec download-remote-session --run-id 12345678 --session-id abc-123

Output:
    Structured JSON output with success status and session file path

Exit Codes:
    0: Success (session file downloaded and located)
    1: Error (download failed, artifact not found, no .jsonl file found)

Examples:
    $ erk exec download-remote-session --gist-url <gist-raw-url> --session-id abc-123
    {
      "success": true,
      "session_id": "abc-123",
      "path": "...",
      "source": "gist"
    }

    $ erk exec download-remote-session --run-id 12345678 --session-id abc-123
    {
      "success": true,
      "session_id": "abc-123",
      "run_id": "12345678",
      "path": "...",
      "artifact_name": "session-abc-123",
      "source": "artifact"
    }
"""

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import click

from erk_shared.context.helpers import require_github, require_repo_root


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


def _find_jsonl_file(directory: Path) -> Path | None:
    """Find a .jsonl file in the given directory.

    Args:
        directory: Directory to search in.

    Returns:
        Path to the first .jsonl file found, or None if not found.
    """
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix == ".jsonl":
            return file_path
    return None


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
    help="Raw gist URL to download session from (preferred method)",
)
@click.option(
    "--run-id",
    help="GitHub Actions workflow run ID (legacy artifact method)",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID (used to locate artifact and name output)",
)
@click.pass_context
def download_remote_session(
    ctx: click.Context,
    gist_url: str | None,
    run_id: str | None,
    session_id: str,
) -> None:
    """Download a session from a GitHub Gist or Actions artifact.

    Supports two modes:
    - Gist mode (--gist-url): Downloads directly from a raw gist URL
    - Artifact mode (--run-id): Downloads from GitHub Actions artifact (legacy)

    Stores the session in .erk/scratch/remote-sessions/{session_id}/.

    The command:
    1. Cleans up existing directory if present (idempotent)
    2. Downloads session from gist or artifact
    3. Returns path to the session file
    """
    # Validate that exactly one source is provided
    if gist_url is None and run_id is None:
        error_output = {
            "success": False,
            "error": "Either --gist-url or --run-id must be provided",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    if gist_url is not None and run_id is not None:
        error_output = {
            "success": False,
            "error": "Cannot use both --gist-url and --run-id together",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

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

    # Gist mode: download directly from URL
    if gist_url is not None:
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
        return

    # Artifact mode (legacy): download from GitHub Actions
    # At this point, run_id is guaranteed to be not None (validated above)
    assert run_id is not None
    github = require_github(ctx)
    artifact_name = f"session-{session_id}"

    # Download the artifact using the GitHub gateway
    success = github.download_run_artifact(repo_root, run_id, artifact_name, session_dir)
    if not success:
        error_output = {
            "success": False,
            "error": f"Failed to download artifact '{artifact_name}' from run {run_id}",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Find the .jsonl file in the downloaded artifact
    jsonl_file = _find_jsonl_file(session_dir)
    if jsonl_file is None:
        error_output = {
            "success": False,
            "error": f"No .jsonl file found in downloaded artifact '{artifact_name}'",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Rename to session.jsonl for predictable access
    session_file = session_dir / "session.jsonl"
    if jsonl_file.name != "session.jsonl":
        jsonl_file.rename(session_file)

    # Output success result
    output = {
        "success": True,
        "session_id": session_id,
        "run_id": run_id,
        "path": str(session_file),
        "artifact_name": artifact_name,
        "source": "artifact",
    }
    click.echo(json.dumps(output))
