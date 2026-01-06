"""Command logging for erk CLI audit trail.

This module provides logging of all erk CLI invocations with context,
similar to zsh's ~/.zsh_history. Used for debugging issues like
"what command deleted my worktree".

Log location: ~/.erk/command_history.jsonl
Format: One JSON object per line (JSONL) for easy parsing and appending.
"""

import atexit
import fcntl
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.git.real import RealGit

# Environment variable to disable command logging
ENV_DISABLE_LOG = "ERK_NO_COMMAND_LOG"

# Maximum log file size in bytes (50MB)
MAX_LOG_SIZE_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class CommandLogEntry:
    """A single command log entry."""

    timestamp: str
    command: str
    args: tuple[str, ...]
    cwd: str
    branch: str | None
    exit_code: int | None
    session_id: str | None
    pid: int


def _get_log_file_path(installation: ErkInstallation | None = None) -> Path:
    """Return path to command history log file.

    Args:
        installation: ErkInstallation instance. If None, uses RealErkInstallation.
                     Passing None is for CLI entry points before context exists.
    """
    if installation is None:
        installation = RealErkInstallation()
    return installation.get_command_log_path()


def _is_logging_disabled() -> bool:
    """Check if command logging is disabled via environment variable."""
    return os.environ.get(ENV_DISABLE_LOG) == "1"


def _get_current_branch(cwd: Path) -> str | None:
    """Get current git branch if in a git repository."""
    git = RealGit()
    # get_git_common_dir returns None gracefully when outside a git repo,
    # whereas get_repository_root raises RuntimeError
    git_dir = git.get_git_common_dir(cwd)
    if git_dir is None:
        return None
    repo_root = git.get_repository_root(cwd)
    return git.get_current_branch(repo_root)


def _get_session_id() -> str | None:
    """Get Claude Code session ID if available."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID")


def _rotate_log_if_needed(log_path: Path) -> None:
    """Rotate log file if it exceeds maximum size."""
    if not log_path.exists():
        return
    if log_path.stat().st_size <= MAX_LOG_SIZE_BYTES:
        return

    # Rotate: rename current to .old (overwriting previous .old)
    old_path = log_path.with_suffix(".jsonl.old")
    if old_path.exists():
        old_path.unlink()
    log_path.rename(old_path)


def _write_entry(log_path: Path, entry_dict: dict[str, str | int | list[str] | None]) -> None:
    """Write a log entry with file locking for concurrent writes."""
    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Rotate if needed (before acquiring lock to avoid holding lock during rename)
    _rotate_log_if_needed(log_path)

    # Open with append mode and exclusive lock
    with log_path.open("a", encoding="utf-8") as f:
        # Acquire exclusive lock for concurrent write safety
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry_dict) + "\n")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def log_command_start(args: list[str], cwd: Path) -> str | None:
    """Log command invocation at start.

    Args:
        args: Command line arguments (sys.argv[1:])
        cwd: Current working directory

    Returns:
        Entry ID (timestamp) for use with log_command_end, or None if logging disabled
    """
    if _is_logging_disabled():
        return None

    timestamp = datetime.now(UTC).isoformat()

    # Build command string from args
    # Extract up to 2 non-flag args as subcommand (e.g., "wt delete")
    # Remaining args are treated as command arguments
    command = "erk"
    remaining_args = list(args)
    subcommand_parts: list[str] = []

    # Take at most 2 subcommand parts (e.g., "wt delete" but not "wt delete foo")
    max_subcommand_depth = 2
    for arg in args:
        if arg.startswith("-") or len(subcommand_parts) >= max_subcommand_depth:
            break
        subcommand_parts.append(arg)
        remaining_args = remaining_args[1:]

    if subcommand_parts:
        command = f"erk {' '.join(subcommand_parts)}"

    entry = {
        "timestamp": timestamp,
        "command": command,
        "args": remaining_args,
        "cwd": str(cwd),
        "branch": _get_current_branch(cwd),
        "exit_code": None,  # Will be filled by log_command_end
        "session_id": _get_session_id(),
        "pid": os.getpid(),
    }

    log_path = _get_log_file_path()
    _write_entry(log_path, entry)

    return timestamp


def log_command_end(entry_id: str | None, exit_code: int) -> None:
    """Log command completion with exit code.

    Args:
        entry_id: Entry ID from log_command_start (timestamp)
        exit_code: Process exit code (0 = success)
    """
    if entry_id is None or _is_logging_disabled():
        return

    # Write a completion entry that references the start entry
    completion_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "type": "completion",
        "start_timestamp": entry_id,
        "exit_code": exit_code,
        "pid": os.getpid(),
    }

    log_path = _get_log_file_path()
    _write_entry(log_path, completion_entry)


def read_log_entries(
    *,
    since: datetime | None,
    until: datetime | None,
    command_filter: str | None,
    cwd_filter: str | None,
    limit: int | None,
) -> list[CommandLogEntry]:
    """Read log entries with optional filters.

    Args:
        since: Only entries after this time
        until: Only entries before this time
        command_filter: Only entries matching this command substring
        cwd_filter: Only entries from this directory (exact match)
        limit: Maximum number of entries to return

    Returns:
        List of matching entries, most recent first
    """
    log_path = _get_log_file_path()
    if not log_path.exists():
        return []

    entries: list[CommandLogEntry] = []
    completion_map: dict[str, int] = {}  # start_timestamp -> exit_code

    # First pass: collect completion entries
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "completion":
                start_ts = data.get("start_timestamp")
                exit_code = data.get("exit_code")
                if start_ts is not None and exit_code is not None:
                    completion_map[start_ts] = exit_code

    # Second pass: collect command entries
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Skip completion entries
            if data.get("type") == "completion":
                continue

            # Parse timestamp
            timestamp_str = data.get("timestamp")
            if timestamp_str is None:
                continue
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                continue

            # Apply time filters
            if since is not None and timestamp < since:
                continue
            if until is not None and timestamp > until:
                continue

            # Apply command filter
            command = data.get("command", "")
            if command_filter is not None and command_filter.lower() not in command.lower():
                continue

            # Apply cwd filter
            entry_cwd = data.get("cwd", "")
            if cwd_filter is not None and entry_cwd != cwd_filter:
                continue

            # Look up exit code from completion entries
            exit_code = completion_map.get(timestamp_str)

            entry = CommandLogEntry(
                timestamp=timestamp_str,
                command=command,
                args=tuple(data.get("args", [])),
                cwd=entry_cwd,
                branch=data.get("branch"),
                exit_code=exit_code,
                session_id=data.get("session_id"),
                pid=data.get("pid", 0),
            )
            entries.append(entry)

    # Sort by timestamp descending (most recent first)
    entries.sort(key=lambda e: e.timestamp, reverse=True)

    # Apply limit
    if limit is not None:
        entries = entries[:limit]

    return entries


def get_cli_args() -> list[str]:
    """Get CLI arguments for logging, skipping the program name."""
    return sys.argv[1:]


def register_exit_handler(entry_id: str | None) -> None:
    """Register an atexit handler to log command completion.

    This ensures logging even on exceptions or SystemExit.

    Args:
        entry_id: Entry ID from log_command_start (timestamp)
    """

    def _log_exit() -> None:
        exc_info = sys.exc_info()
        exc = exc_info[1]
        if isinstance(exc, SystemExit):
            exit_code = exc.code if isinstance(exc.code, int) else 1
        elif exc is not None:
            exit_code = 1
        else:
            exit_code = 0
        log_command_end(entry_id, exit_code)

    atexit.register(_log_exit)


def is_numeric_string(s: str) -> bool:
    """Check if string represents an integer (possibly negative)."""
    if not s:
        return False
    if s[0] in "+-":
        return s[1:].isdigit() if len(s) > 1 else False
    return s.isdigit()


def is_iso_datetime_format(s: str) -> bool:
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


def parse_relative_time(value: str) -> timedelta | None:
    """Parse relative time string like '1 hour ago' into a timedelta.

    Args:
        value: String like "1 hour ago", "2 days ago", "30 minutes ago"

    Returns:
        timedelta if valid, None if invalid format
    """
    value = value.strip().lower()
    if not value.endswith(" ago"):
        return None

    parts = value[:-4].strip().split()
    if len(parts) != 2:
        return None

    amount_str = parts[0]
    if not is_numeric_string(amount_str):
        return None

    amount = int(amount_str)
    unit = parts[1].rstrip("s")  # "hours" -> "hour"

    if unit == "minute":
        return timedelta(minutes=amount)
    elif unit == "hour":
        return timedelta(hours=amount)
    elif unit == "day":
        return timedelta(days=amount)
    elif unit == "week":
        return timedelta(weeks=amount)
    return None


def format_relative_time(timestamp_str: str) -> str:
    """Format an ISO timestamp as relative time (e.g., '5m ago').

    Args:
        timestamp_str: ISO format timestamp

    Returns:
        Relative time string, or truncated timestamp if parsing fails
    """
    if not is_iso_datetime_format(timestamp_str):
        return timestamp_str[:19]

    dt = datetime.fromisoformat(timestamp_str)
    now = datetime.now(UTC)
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        mins = int(delta.total_seconds() / 60)
        return f"{mins}m ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        return f"{delta.days}d ago"
