"""Download a Claude Code session artifact from a GitHub Actions workflow run.

This exec command downloads a session artifact from a workflow run and stores
it in the .erk/scratch/remote-sessions/ directory for learn workflow processing.

Usage:
    erk exec download-remote-session --run-id 12345678 --session-id abc-123

Output:
    Structured JSON output with success status and session file path

Exit Codes:
    0: Success (session file downloaded and located)
    1: Error (download failed, artifact not found, no .jsonl file found)

Examples:
    $ erk exec download-remote-session --run-id 12345678 --session-id abc-123
    {
      "success": true,
      "session_id": "abc-123",
      "run_id": "12345678",
      "path": "...",
      "artifact_name": "session-abc-123"
    }
"""

import json
import shutil
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


@click.command(name="download-remote-session")
@click.option(
    "--run-id",
    required=True,
    help="GitHub Actions workflow run ID",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID (used to locate artifact)",
)
@click.pass_context
def download_remote_session(
    ctx: click.Context,
    run_id: str,
    session_id: str,
) -> None:
    """Download a session artifact from a GitHub Actions workflow run.

    Downloads the artifact named 'session-{session_id}' from the specified
    workflow run and stores it in .erk/scratch/remote-sessions/{session_id}/.

    The command:
    1. Cleans up existing directory if present (idempotent)
    2. Downloads artifact from GitHub Actions
    3. Finds the .jsonl file in the downloaded artifact
    4. Returns path to the session file
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    artifact_name = f"session-{session_id}"

    # Get or create the remote sessions directory
    session_dir = _get_remote_sessions_dir(repo_root, session_id)

    # Clean up existing directory contents for idempotent re-downloads
    if session_dir.exists():
        for item in session_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

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
    }
    click.echo(json.dumps(output))
