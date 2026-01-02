"""Log command for querying erk command history.

Provides access to the command audit trail stored in ~/.erk/command_history.jsonl.
"""

from datetime import UTC, datetime

import click

from erk.core.command_log import (
    CommandLogEntry,
    format_relative_time,
    is_iso_datetime_format,
    parse_relative_time,
    read_log_entries,
)


def _parse_since(value: str | None) -> datetime | None:
    """Parse --since value into datetime.

    Supports:
    - Relative: "1 hour ago", "2 days ago", "30 minutes ago"
    - ISO format: "2024-01-01T00:00:00"
    """
    if value is None:
        return None

    value_lower = value.strip().lower()

    # Try relative time parsing
    delta = parse_relative_time(value_lower)
    if delta is not None:
        return datetime.now(UTC) - delta

    # Try ISO format
    if not is_iso_datetime_format(value_lower):
        raise click.BadParameter(
            f"Invalid time format: {value}. Use 'N unit ago' (e.g., '1 hour ago') "
            "or ISO format (e.g., '2024-01-01T00:00:00')"
        )
    return datetime.fromisoformat(value_lower)


def _format_entry_line(entry: CommandLogEntry, show_cwd: bool, show_full: bool) -> str:
    """Format a single log entry for display."""
    # Get time display
    if show_full:
        # For full mode, parse and format as full timestamp
        if is_iso_datetime_format(entry.timestamp):
            dt = datetime.fromisoformat(entry.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = entry.timestamp[:19]
    else:
        time_str = format_relative_time(entry.timestamp)

    # Build command display
    cmd_display = entry.command
    if entry.args:
        cmd_display += " " + " ".join(entry.args)

    # Exit code indicator
    if entry.exit_code is None:
        status = click.style("?", fg="yellow")
    elif entry.exit_code == 0:
        status = click.style("✓", fg="green")
    else:
        status = click.style("✗", fg="red")

    # Format line
    parts = [
        click.style(f"[{time_str}]", dim=True),
        status,
        cmd_display,
    ]

    if show_cwd:
        parts.append(click.style(f"({entry.cwd})", dim=True))

    return " ".join(parts)


@click.command("log")
@click.option("--since", "-s", help="Show entries since time (e.g., '1 hour ago', '2024-01-01')")
@click.option("--filter", "-f", "command_filter", help="Filter by command substring")
@click.option("--cwd", "-c", "cwd_filter", help="Filter by working directory")
@click.option("--limit", "-n", type=int, help="Maximum entries to show (default: 50)")
@click.option("--full", is_flag=True, help="Show full timestamps and details")
@click.option("--show-cwd", is_flag=True, help="Show working directory for each entry")
def log_cmd(
    since: str | None,
    command_filter: str | None,
    cwd_filter: str | None,
    limit: int | None,
    full: bool,
    show_cwd: bool,
) -> None:
    """Show erk command history.

    Displays recent erk command invocations with their status.

    \b
    Examples:
      erk log                        # Show recent commands
      erk log --since "1 hour ago"   # Commands from last hour
      erk log --filter "wt delete"   # Only worktree deletions
      erk log --cwd /path/to/repo    # Commands from specific directory
      erk log -n 10                  # Show last 10 commands
    """
    # Parse since option
    since_dt = _parse_since(since)

    # Default limit
    if limit is None:
        limit = 50

    # Read entries
    entries = read_log_entries(
        since=since_dt,
        until=None,
        command_filter=command_filter,
        cwd_filter=cwd_filter,
        limit=limit,
    )

    if not entries:
        click.echo(click.style("No matching entries found.", dim=True))
        return

    # Display entries
    for entry in entries:
        click.echo(_format_entry_line(entry, show_cwd, full))

    # Show count if there might be more
    if len(entries) == limit:
        click.echo(click.style(f"\n(Showing {limit} most recent. Use --limit for more.)", dim=True))
