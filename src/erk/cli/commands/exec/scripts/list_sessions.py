#!/usr/bin/env python3
"""List Claude Code sessions for the current project with metadata.

This command discovers sessions in the Claude Code project directory,
extracts metadata (timestamps, summaries), and provides branch context
for intelligent session selection.

Usage:
    erk exec list-sessions

Output:
    JSON object with success status, branch context, and session list

Exit Codes:
    0: Success
    1: Error (project directory not found or other error)

Examples:
    $ erk exec list-sessions
    {
      "success": true,
      "branch_context": {
        "current_branch": "feature-xyz",
        "trunk_branch": "master",
        "is_on_trunk": false
      },
      "current_session_id": "abc123-def456",
      "sessions": [...],
      "project_dir": "claude-code-project"
    }
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_claude_installation, require_cwd, require_git
from erk_shared.git.abc import Git
from erk_shared.learn.extraction.claude_installation.abc import ClaudeInstallation, Session
from erk_shared.learn.extraction.session_schema import (
    extract_first_user_message_text,
    extract_git_branch,
)


@dataclass(frozen=True)
class BranchContext:
    """Git branch context for session selection behavior."""

    current_branch: str
    trunk_branch: str
    is_on_trunk: bool


@dataclass(frozen=True)
class SessionInfo:
    """Metadata for a session log file."""

    session_id: str
    mtime_display: str
    mtime_relative: str
    mtime_unix: float
    size_bytes: int
    summary: str
    is_current: bool
    branch: str | None  # Git branch active during session
    session_path: str  # Absolute path to session .jsonl file


@dataclass(frozen=True)
class ListSessionsResult:
    """Success result with session list and context."""

    success: bool
    branch_context: dict[str, str | bool]
    current_session_id: str | None
    sessions: list[dict[str, str | float | int | bool]]
    project_dir: str
    filtered_count: int  # Count of sessions filtered by --min-size


@dataclass(frozen=True)
class ListSessionsError:
    """Error result when listing sessions fails."""

    success: bool
    error: str
    help: str


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


def _list_sessions_from_store(
    *,
    claude_installation: ClaudeInstallation,
    cwd: Path,
    current_session_id: str | None,
    limit: int,
    min_size: int,
) -> tuple[list[SessionInfo], int]:
    """List sessions from claude installation sorted by modification time.

    Args:
        claude_installation: Claude installation to query
        cwd: Current working directory (project identifier)
        current_session_id: Current session ID (for marking)
        limit: Maximum number of sessions to return
        min_size: Minimum session size in bytes (filters out tiny sessions)

    Returns:
        Tuple of (sessions list, count of sessions filtered by min_size)
    """
    # Check if project exists
    if not claude_installation.has_project(cwd):
        return [], 0

    # Get all sessions first to count filtered
    all_sessions = claude_installation.find_sessions(
        cwd,
        current_session_id=current_session_id,
        min_size=0,
        limit=1000,
        include_agents=False,
    )

    # Filter by size
    filtered_sessions: list[Session]
    if min_size > 0:
        filtered_sessions = [s for s in all_sessions if s.size_bytes >= min_size]
        filtered_count = len(all_sessions) - len(filtered_sessions)
    else:
        filtered_sessions = all_sessions
        filtered_count = 0

    # Apply limit
    limited_sessions = filtered_sessions[:limit]

    # Convert to SessionInfo with summaries and branch info
    session_infos: list[SessionInfo] = []
    for session in limited_sessions:
        # Read session content for summary and branch extraction
        content = claude_installation.read_session(cwd, session.session_id, include_agents=False)
        summary = ""
        branch: str | None = None
        if content is not None:
            summary = extract_first_user_message_text(content.main_content, max_length=60)
            branch = extract_git_branch(content.main_content)

        # Determine if this is the current session
        is_current = session.session_id == current_session_id

        # Get session file path
        session_path = claude_installation.get_session_path(cwd, session.session_id)
        session_path_str = str(session_path) if session_path is not None else ""

        # Extract branch from session content (gitBranch field in entries)
        branch: str | None = None
        if content is not None:
            for line in content.main_content.split("\n"):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if "gitBranch" in entry:
                        branch = entry["gitBranch"]
                        break
                except json.JSONDecodeError:
                    continue

        session_infos.append(
            SessionInfo(
                session_id=session.session_id,
                mtime_display=format_display_time(session.modified_at),
                mtime_relative=format_relative_time(session.modified_at),
                mtime_unix=session.modified_at,
                size_bytes=session.size_bytes,
                summary=summary,
                is_current=is_current,
                branch=branch,
                session_path=session_path_str,
            )
        )

    return session_infos, filtered_count


@click.command(name="list-sessions")
@click.option(
    "--limit",
    default=10,
    type=int,
    help="Maximum number of sessions to list",
)
@click.option(
    "--min-size",
    default=0,
    type=int,
    help="Minimum session size in bytes (filters out tiny sessions)",
)
@click.option(
    "--session-id",
    default=None,
    type=str,
    help="Current session ID (for marking the current session)",
)
@click.pass_context
def list_sessions(ctx: click.Context, limit: int, min_size: int, session_id: str | None) -> None:
    """List Claude Code sessions with metadata for the current project.

    Discovers sessions in the project directory, extracts metadata
    (timestamps, summaries), and provides branch context.
    """
    git = require_git(ctx)
    claude_installation = require_claude_installation(ctx)
    cwd = require_cwd(ctx)

    # Check if project exists
    if not claude_installation.has_project(cwd):
        error = ListSessionsError(
            success=False,
            error=f"No Claude Code project found for: {cwd}",
            help="Make sure you're in a directory with Claude Code sessions",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    # Get branch context
    branch_context = get_branch_context(git, cwd)

    # List sessions from store
    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=claude_installation,
        cwd=cwd,
        current_session_id=session_id,
        limit=limit,
        min_size=min_size,
    )

    # Build result
    result = ListSessionsResult(
        success=True,
        branch_context={
            "current_branch": branch_context.current_branch,
            "trunk_branch": branch_context.trunk_branch,
            "is_on_trunk": branch_context.is_on_trunk,
        },
        current_session_id=session_id,
        sessions=[asdict(s) for s in sessions],
        project_dir="claude-code-project",  # Abstract - don't expose filesystem paths
        filtered_count=filtered_count,
    )

    click.echo(json.dumps(asdict(result), indent=2))
