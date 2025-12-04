#!/usr/bin/env python3
"""List Claude Code sessions for the current project with metadata.

This command discovers sessions in the Claude Code project directory,
extracts metadata (timestamps, summaries), and provides branch context
for intelligent session selection.

Usage:
    dot-agent run erk list-sessions

Output:
    JSON object with success status, branch context, and session list

Exit Codes:
    0: Success
    1: Error (project directory not found or other error)

Examples:
    $ dot-agent run erk list-sessions
    {
      "success": true,
      "branch_context": {
        "current_branch": "feature-xyz",
        "trunk_branch": "master",
        "is_on_trunk": false
      },
      "current_session_id": "abc123-def456",
      "sessions": [...],
      "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-erk"
    }
"""

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.find_project_dir import (
    ProjectError,
    find_project_info,
)


@dataclass
class BranchContext:
    """Git branch context for session selection behavior."""

    current_branch: str
    trunk_branch: str
    is_on_trunk: bool


@dataclass
class SessionInfo:
    """Metadata for a session log file."""

    session_id: str
    mtime_display: str
    mtime_relative: str
    mtime_unix: float
    size_bytes: int
    summary: str
    is_current: bool


@dataclass
class ListSessionsResult:
    """Success result with session list and context."""

    success: bool
    branch_context: dict[str, str | bool]
    current_session_id: str | None
    sessions: list[dict[str, str | float | int | bool]]
    project_dir: str


@dataclass
class ListSessionsError:
    """Error result when listing sessions fails."""

    success: bool
    error: str
    help: str


def get_branch_context(cwd: Path) -> BranchContext:
    """Get git branch context for determining session selection behavior.

    Args:
        cwd: Current working directory

    Returns:
        BranchContext with current branch, trunk branch, and trunk status
    """
    # Get current branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        current_branch = result.stdout.strip()
    except subprocess.CalledProcessError:
        current_branch = ""

    # Get trunk branch from remote HEAD
    trunk_branch = "main"
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        # Format: refs/remotes/origin/main or refs/remotes/origin/master
        ref = result.stdout.strip()
        if ref:
            trunk_branch = ref.replace("refs/remotes/origin/", "")
    except subprocess.CalledProcessError:
        # Fallback: check if master exists
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", "refs/heads/master"],
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd,
            )
            trunk_branch = "master"
        except subprocess.CalledProcessError:
            trunk_branch = "main"

    return BranchContext(
        current_branch=current_branch,
        trunk_branch=trunk_branch,
        is_on_trunk=current_branch == trunk_branch,
    )


def get_current_session_id() -> str | None:
    """Extract current session ID from SESSION_CONTEXT environment variable.

    The SESSION_CONTEXT env var contains: session_id=<uuid>

    Returns:
        Session ID string or None if not found
    """
    ctx = os.environ.get("SESSION_CONTEXT", "")
    if "session_id=" in ctx:
        return ctx.split("session_id=")[1].strip()
    return None


def format_relative_time(mtime: float) -> str:
    """Format modification time as human-readable relative time.

    Args:
        mtime: Unix timestamp (seconds since epoch)

    Returns:
        Human-readable relative time string

    Examples:
        >>> format_relative_time(time.time() - 10)
        'just now'
        >>> format_relative_time(time.time() - 180)
        '3m ago'
        >>> format_relative_time(time.time() - 7200)
        '2h ago'
    """
    now = time.time()
    delta = now - mtime

    if delta < 30:
        return "just now"
    if delta < 3600:  # < 1 hour
        minutes = int(delta / 60)
        return f"{minutes}m ago"
    if delta < 86400:  # < 24 hours
        hours = int(delta / 3600)
        return f"{hours}h ago"
    if delta < 604800:  # < 7 days
        days = int(delta / 86400)
        return f"{days}d ago"
    # >= 7 days: show absolute date
    return format_display_time(mtime)


def format_display_time(mtime: float) -> str:
    """Format modification time as display string.

    Args:
        mtime: Unix timestamp (seconds since epoch)

    Returns:
        Formatted date string like "Dec 3, 11:38 AM"
    """
    import datetime

    dt = datetime.datetime.fromtimestamp(mtime)
    return dt.strftime("%b %-d, %-I:%M %p")


def extract_summary(session_path: Path, max_length: int = 60) -> str:
    """Extract summary from session log (first user message text).

    Args:
        session_path: Path to session JSONL file
        max_length: Maximum summary length

    Returns:
        First user message text, truncated to max_length
    """
    try:
        with session_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "user":
                        continue

                    message = entry.get("message", {})
                    content = message.get("content", "")

                    # Content can be string or list of content blocks
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        # Find first text block
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                break
                            elif isinstance(block, str):
                                text = block
                                break
                        else:
                            continue
                    else:
                        continue

                    # Clean up the text
                    text = text.strip()
                    if not text:
                        continue

                    # Truncate with ellipsis if needed
                    if len(text) > max_length:
                        return text[: max_length - 3] + "..."
                    return text

                except json.JSONDecodeError:
                    continue

    except OSError:
        pass

    return ""


def list_sessions(
    project_dir: Path, current_session_id: str | None, limit: int = 10
) -> list[SessionInfo]:
    """List sessions in project directory sorted by modification time.

    Args:
        project_dir: Path to Claude Code project directory
        current_session_id: Current session ID (for marking)
        limit: Maximum number of sessions to return

    Returns:
        List of SessionInfo objects, newest first
    """
    sessions: list[SessionInfo] = []

    if not project_dir.exists():
        return sessions

    # Collect session files (exclude agent logs)
    session_files: list[tuple[Path, float]] = []
    for log_file in project_dir.iterdir():
        if not log_file.is_file():
            continue
        if log_file.suffix != ".jsonl":
            continue
        if log_file.name.startswith("agent-"):
            continue

        mtime = log_file.stat().st_mtime
        session_files.append((log_file, mtime))

    # Sort by mtime descending (newest first)
    session_files.sort(key=lambda x: x[1], reverse=True)

    # Take limit
    for log_file, mtime in session_files[:limit]:
        session_id = log_file.stem
        size_bytes = log_file.stat().st_size
        summary = extract_summary(log_file)

        sessions.append(
            SessionInfo(
                session_id=session_id,
                mtime_display=format_display_time(mtime),
                mtime_relative=format_relative_time(mtime),
                mtime_unix=mtime,
                size_bytes=size_bytes,
                summary=summary,
                is_current=(session_id == current_session_id),
            )
        )

    return sessions


@click.command(name="list-sessions")
@click.option(
    "--limit",
    default=10,
    type=int,
    help="Maximum number of sessions to list",
)
def list_sessions_cli(limit: int) -> None:
    """List Claude Code sessions with metadata for the current project.

    Discovers sessions in the project directory, extracts metadata
    (timestamps, summaries), and provides branch context.
    """
    cwd = Path(os.getcwd())

    # Find project directory
    project_result = find_project_info(cwd)

    if isinstance(project_result, ProjectError):
        error = ListSessionsError(
            success=False,
            error=project_result.error,
            help=project_result.help,
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    project_dir = Path(project_result.project_dir)

    # Get branch context
    branch_context = get_branch_context(cwd)

    # Get current session ID from environment
    current_session_id = get_current_session_id()

    # List sessions
    sessions = list_sessions(project_dir, current_session_id, limit=limit)

    # Build result
    result = ListSessionsResult(
        success=True,
        branch_context={
            "current_branch": branch_context.current_branch,
            "trunk_branch": branch_context.trunk_branch,
            "is_on_trunk": branch_context.is_on_trunk,
        },
        current_session_id=current_session_id,
        sessions=[asdict(s) for s in sessions],
        project_dir=str(project_dir),
    )

    click.echo(json.dumps(asdict(result), indent=2))
