#!/usr/bin/env python3
"""List Claude Code sessions for the current project with metadata.

This command discovers sessions in the Claude Code project directory,
extracts metadata (timestamps, summaries), and provides branch context
for intelligent session selection.

Usage:
    erk kit exec erk list-sessions

Output:
    JSON object with success status, branch context, and session list

Exit Codes:
    0: Success
    1: Error (project directory not found or other error)

Examples:
    $ erk kit exec erk list-sessions
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

from erk_shared.context.helpers import require_cwd, require_git, require_session_store
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore, Session
from erk_shared.git.abc import Git


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
    filtered_count: int  # Count of sessions filtered by --min-size


@dataclass
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


def extract_text_from_blocks(blocks: list[dict | str]) -> str:
    """Extract the first text string from a list of content blocks."""
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
        elif isinstance(block, str):
            return block
    return ""


def extract_summary(content: str, max_length: int = 60) -> str:
    """Extract summary from session content (first user message text).

    Args:
        content: Raw JSONL session content
        max_length: Maximum summary length

    Returns:
        First user message text, truncated to max_length
    """
    for line in content.split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "user":
            continue

        message = entry.get("message", {})
        content_field = message.get("content", "")

        # Content can be string or list of content blocks
        if isinstance(content_field, str):
            text = content_field
        elif isinstance(content_field, list):
            # Find first text block
            text = extract_text_from_blocks(content_field)
            if not text:
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

    return ""


def _list_sessions_from_store(
    session_store: ClaudeCodeSessionStore,
    cwd: Path,
    current_session_id: str | None,
    limit: int = 10,
    min_size: int = 0,
) -> tuple[list[SessionInfo], int]:
    """List sessions from session store sorted by modification time.

    Args:
        session_store: Session store to query
        cwd: Current working directory (project identifier)
        current_session_id: Current session ID (for marking)
        limit: Maximum number of sessions to return
        min_size: Minimum session size in bytes (filters out tiny sessions)

    Returns:
        Tuple of (sessions list, count of sessions filtered by min_size)
    """
    # Check if project exists
    if not session_store.has_project(cwd):
        return [], 0

    # Get all sessions first to count filtered
    all_sessions = session_store.find_sessions(
        cwd, current_session_id=current_session_id, min_size=0, limit=1000
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

    # Convert to SessionInfo with summaries
    session_infos: list[SessionInfo] = []
    for session in limited_sessions:
        # Read session content for summary extraction
        content = session_store.read_session(cwd, session.session_id, include_agents=False)
        summary = ""
        if content is not None:
            summary = extract_summary(content.main_content)

        # Determine if this is the current session
        is_current = session.session_id == current_session_id

        session_infos.append(
            SessionInfo(
                session_id=session.session_id,
                mtime_display=format_display_time(session.modified_at),
                mtime_relative=format_relative_time(session.modified_at),
                mtime_unix=session.modified_at,
                size_bytes=session.size_bytes,
                summary=summary,
                is_current=is_current,
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
def list_sessions(
    ctx: click.Context, limit: int, min_size: int, session_id: str | None
) -> None:
    """List Claude Code sessions with metadata for the current project.

    Discovers sessions in the project directory, extracts metadata
    (timestamps, summaries), and provides branch context.
    """
    git = require_git(ctx)
    session_store = require_session_store(ctx)
    cwd = require_cwd(ctx)

    # Check if project exists
    if not session_store.has_project(cwd):
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
        session_store, cwd, session_id, limit=limit, min_size=min_size
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
