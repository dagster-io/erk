"""Log command for querying erk command history.

Provides access to the command audit trail stored in ~/.erk/command_history.jsonl.
"""

from datetime import UTC, datetime, timedelta

import click

from erk.core.command_log import CommandLogEntry, read_log_entries


def _is_numeric_string(s: str) -> bool:
    """Check if string represents an integer (possibly negative)."""
    if not s:
        return False
    if s[0] in "+-":
        return s[1:].isdigit() if len(s) > 1 else False
    return s.isdigit()


def _is_iso_datetime_format(s: str) -> bool:
    """Check if string looks like an ISO datetime format.

    Validates basic structure: YYYY-MM-DDTHH:MM:SS with optional timezone.
    """
    # Basic length check (minimum: 2024-01-01 = 10 chars)
    if len(s) < 10:
        return False
    # Check date part structure
    if len(s) >= 10 and not (s[4] == "-" and s[7] == "-"):
        return False
    # Check year/month/day are digits
    if not (s[:4].isdigit() and s[5:7].isdigit() and s[8:10].isdigit()):
        return False
    return True


def _parse_since(value: str | None) -> datetime | None:
    """Parse --since value into datetime.

    Supports:
    - Relative: "1 hour ago", "2 days ago", "30 minutes ago"
    - ISO format: "2024-01-01T00:00:00"
    """
    if value is None:
        return None

    value = value.strip().lower()

    # Try relative time parsing
    if value.endswith(" ago"):
        parts = value[:-4].strip().split()
        if len(parts) == 2:
            amount_str = parts[0]
            if not _is_numeric_string(amount_str):
                raise click.BadParameter(f"Invalid time amount: {amount_str}")

            amount = int(amount_str)
            unit = parts[1].rstrip("s")  # "hours" -> "hour"
            now = datetime.now(UTC)

            if unit == "minute":
                return now - timedelta(minutes=amount)
            elif unit == "hour":
                return now - timedelta(hours=amount)
            elif unit == "day":
                return now - timedelta(days=amount)
            elif unit == "week":
                return now - timedelta(weeks=amount)
            else:
                raise click.BadParameter(f"Unknown time unit: {unit}")

    # Try ISO format
    if not _is_iso_datetime_format(value):
        raise click.BadParameter(
            f"Invalid time format: {value}. Use 'N unit ago' (e.g., '1 hour ago') "
            "or ISO format (e.g., '2024-01-01T00:00:00')"
        )
    return datetime.fromisoformat(value)


def _format_entry_line(entry: CommandLogEntry, show_cwd: bool, show_full: bool) -> str:
    """Format a single log entry for display."""

    # Parse timestamp for display
    try:
        dt = datetime.fromisoformat(entry.timestamp)
        if show_full:
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Show relative time for recent entries
            now = datetime.now(UTC)
            delta = now - dt
            if delta < timedelta(minutes=1):
                time_str = "just now"
            elif delta < timedelta(hours=1):
                mins = int(delta.total_seconds() / 60)
                time_str = f"{mins}m ago"
            elif delta < timedelta(days=1):
                hours = int(delta.total_seconds() / 3600)
                time_str = f"{hours}h ago"
            else:
                days = delta.days
                time_str = f"{days}d ago"
    except ValueError:
        time_str = entry.timestamp[:19]

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
