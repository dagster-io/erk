"""List Claude Code sessions for the current worktree."""

import datetime
import json
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from erk.core.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore


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


def extract_text_from_blocks(blocks: list[dict | str]) -> str:
    """Extract the first text string from a list of content blocks."""
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
        elif isinstance(block, str):
            return block
    return ""


def extract_summary(content: str, max_length: int = 50) -> str:
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
        # Skip lines that don't look like JSON objects
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        entry = json.loads(stripped)

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


def _list_sessions_impl(
    session_store: ClaudeCodeSessionStore,
    cwd: Path,
    limit: int,
) -> None:
    """Implementation of session listing logic.

    Args:
        session_store: Session store to query
        cwd: Current working directory (project identifier)
        limit: Maximum number of sessions to show
    """
    # Check if project exists
    if not session_store.has_project(cwd):
        click.echo(f"No Claude Code sessions found for: {cwd}", err=True)
        raise SystemExit(1)

    # Get sessions
    sessions = session_store.find_sessions(cwd, min_size=0, limit=limit)

    if not sessions:
        click.echo("No sessions found.", err=True)
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("time", no_wrap=True)
    table.add_column("size", no_wrap=True, justify="right")
    table.add_column("summary", no_wrap=False)

    for session in sessions:
        # Read session content for summary extraction
        content = session_store.read_session(cwd, session.session_id, include_agents=False)
        summary = ""
        if content is not None:
            summary = extract_summary(content.main_content)

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
@click.pass_obj
def list_sessions(ctx: ErkContext, limit: int) -> None:
    """List Claude Code sessions for the current worktree.

    Shows a table with session ID, time, size, and summary (first user message).
    """
    _list_sessions_impl(
        ctx.session_store,
        ctx.cwd,
        limit,
    )
