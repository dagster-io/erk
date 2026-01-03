"""List Claude Code sessions for the current worktree."""

import datetime
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from erk.core.context import ErkContext
from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.extraction.session_schema import extract_first_user_message_text


def format_relative_time(mtime: float) -> str:
    """Format modification time as human-readable relative time.

    Args:
        mtime: Unix timestamp (seconds since epoch)

    Returns:
        Human-readable relative time string
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
    dt = datetime.datetime.fromtimestamp(mtime)
    return dt.strftime("%b %-d, %-I:%M %p")


def format_size(size_bytes: int) -> str:
    """Format size in bytes as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string like "45KB"
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024}KB"
    return f"{size_bytes // (1024 * 1024)}MB"


def _list_sessions_impl(
    claude_installation: ClaudeInstallation,
    cwd: Path,
    limit: int,
    include_agents: bool,
) -> None:
    """Implementation of session listing logic.

    Args:
        claude_installation: Claude installation to query
        cwd: Current working directory (project identifier)
        limit: Maximum number of sessions to show
        include_agents: Whether to include agent sessions in the listing
    """
    # Check if project exists
    if not claude_installation.has_project(cwd):
        click.echo(f"No Claude Code sessions found for: {cwd}", err=True)
        raise SystemExit(1)

    # Get sessions
    sessions = claude_installation.find_sessions(
        cwd,
        current_session_id=None,
        min_size=0,
        limit=limit,
        include_agents=include_agents,
    )

    if not sessions:
        click.echo("No sessions found.", err=True)
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("id", style="cyan", no_wrap=True)
    if include_agents:
        table.add_column("parent", no_wrap=True)
    table.add_column("time", no_wrap=True)
    table.add_column("size", no_wrap=True, justify="right")
    table.add_column("summary", no_wrap=False)

    for session in sessions:
        # Read session content for summary extraction
        content = claude_installation.read_session(cwd, session.session_id, include_agents=False)
        summary = ""
        if content is not None:
            summary = extract_first_user_message_text(content.main_content, max_length=50)

        if include_agents:
            # Show first 8 chars of parent_session_id for agents, empty for main sessions
            parent_short = session.parent_session_id[:8] if session.parent_session_id else ""
            table.add_row(
                session.session_id,
                parent_short,
                format_relative_time(session.modified_at),
                format_size(session.size_bytes),
                summary,
            )
        else:
            table.add_row(
                session.session_id,
                format_relative_time(session.modified_at),
                format_size(session.size_bytes),
                summary,
            )

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)


@click.command("list")
@click.option(
    "--limit",
    default=10,
    type=int,
    help="Maximum number of sessions to list",
)
@click.option(
    "--include-agents",
    is_flag=True,
    default=False,
    help="Include agent sessions in the listing",
)
@click.pass_obj
def list_sessions(ctx: ErkContext, limit: int, include_agents: bool) -> None:
    """List Claude Code sessions for the current worktree.

    Shows a table with session ID, time, size, and summary (first user message).
    """
    _list_sessions_impl(
        ctx.claude_installation,
        ctx.cwd,
        limit,
        include_agents,
    )
