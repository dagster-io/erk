#!/usr/bin/env python3
"""Capture Claude Code session info for CI workflows.

This command outputs session information in shell-compatible format,
designed for use in GitHub Actions workflows to capture and upload
session artifacts.

Usage:
    # Capture session info for current directory
    erk exec capture-session-info

    # Capture session info for specific path
    erk exec capture-session-info --path /some/path

Output:
    Shell-compatible variable assignments (when session found):
        SESSION_ID=abc123
        SESSION_FILE=/path/to/.claude/projects/-encoded-path/abc123.jsonl

    Error message to stderr (when session not found):
        No session file found in project directory
        # or
        Project directory not found for: /some/path

Exit Codes:
    0: Success (session found and info output)
    1: No session found (project exists but no sessions)
    2: Project directory not found

Examples:
    # Direct usage in shell
    $ eval "$(erk exec capture-session-info)"
    $ echo "$SESSION_ID"
    abc123

    # In GitHub Actions workflow
    - name: Capture session ID
      id: session
      run: |
        if OUTPUT=$(erk exec capture-session-info --path "$GITHUB_WORKSPACE"); then
          eval "$OUTPUT"
          echo "session_id=$SESSION_ID" >> "$GITHUB_OUTPUT"
          echo "session_file=$SESSION_FILE" >> "$GITHUB_OUTPUT"
        fi
"""

import os
from pathlib import Path

import click

from erk_shared.context.helpers import require_claude_installation
from erk_shared.learn.extraction.claude_installation.abc import ClaudeInstallation


def encode_path_to_project_folder(path: Path) -> str:
    """Encode filesystem path to Claude Code project folder name.

    Claude Code uses a simple encoding scheme:
    - Replace "/" with "-"
    - Replace "." with "-"

    Args:
        path: Filesystem path to encode

    Returns:
        Encoded path suitable for project folder name
    """
    return str(path).replace("/", "-").replace(".", "-")


def capture_session(path: Path, installation: ClaudeInstallation) -> tuple[str, str] | None:
    """Find the latest session for a given path.

    Args:
        path: Filesystem path to find session for
        installation: ClaudeInstallation gateway for accessing projects directory

    Returns:
        Tuple of (session_id, session_file_path) if found, None otherwise
    """
    if not installation.projects_dir_exists():
        return None

    projects_dir = installation.get_projects_dir_path()
    encoded_path = encode_path_to_project_folder(path)
    project_dir = projects_dir / encoded_path

    if not project_dir.exists():
        return None

    # Find the latest main session (not agent logs)
    latest_session: tuple[str, Path, float] | None = None

    for log_file in project_dir.iterdir():
        if log_file.is_file() and log_file.suffix == ".jsonl":
            # Skip agent logs
            if log_file.name.startswith("agent-"):
                continue

            mtime = log_file.stat().st_mtime
            if latest_session is None or mtime > latest_session[2]:
                session_id = log_file.stem
                latest_session = (session_id, log_file, mtime)

    if latest_session is None:
        return None

    return (latest_session[0], str(latest_session[1]))


@click.command(name="capture-session-info")
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to find session for (defaults to current directory)",
)
@click.pass_context
def capture_session_info(ctx: click.Context, path: Path | None) -> None:
    """Capture Claude Code session info for CI workflows.

    Outputs shell-compatible variable assignments for SESSION_ID and SESSION_FILE.
    Designed for use with eval in shell scripts.
    """
    installation = require_claude_installation(ctx)

    # Default to current directory if no path specified
    if path is None:
        path = Path(os.getcwd())

    result = capture_session(path, installation)

    if result is not None:
        session_id, session_file = result
        # Output shell-compatible variable assignments
        click.echo(f"SESSION_ID={session_id}")
        click.echo(f"SESSION_FILE={session_file}")
        return

    # Check if project directory exists to give appropriate error
    projects_dir = installation.get_projects_dir_path()
    encoded_path = encode_path_to_project_folder(path)
    project_dir = projects_dir / encoded_path

    if not project_dir.exists():
        click.echo(f"Project directory not found for: {path}", err=True)
        raise SystemExit(2)
    click.echo("No session file found in project directory", err=True)
    raise SystemExit(1)
