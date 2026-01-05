"""Hook execution logging I/O functions."""

import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.hooks.types import HookExecutionLog, HookExitStatus

# Constants for truncation limits
MAX_STDOUT_BYTES = 10 * 1024  # 10KB
MAX_STDERR_BYTES = 10 * 1024  # 10KB
MAX_STDIN_BYTES = 2 * 1024  # 2KB


def _get_repo_root() -> Path | None:
    """Get the repository root via git rev-parse.

    Returns:
        Path to git repository root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def get_hook_log_dir(session_id: str, hook_id: str, repo_root: Path | None = None) -> Path:
    """Get the directory for hook logs.

    Args:
        session_id: Claude Code session ID
        hook_id: Hook identifier (e.g., "session-id-injector-hook")
        repo_root: Repository root path (uses git to detect if not provided)

    Returns:
        Path to .erk/scratch/sessions/{session_id}/hooks/{hook_id}/
    """
    if repo_root is None:
        repo_root = _get_repo_root()
    if repo_root is None:
        # Fallback to cwd if not in a git repo (shouldn't happen in practice)
        repo_root = Path.cwd()
    return repo_root / ".erk" / "scratch" / "sessions" / session_id / "hooks" / hook_id


def write_hook_log(log: HookExecutionLog, repo_root: Path | None = None) -> Path | None:
    """Write a hook execution log to the appropriate directory.

    Args:
        log: HookExecutionLog to write
        repo_root: Repository root path (uses git to detect if not provided)

    Returns:
        Path to written log file, or None if session_id is missing
    """
    if log.session_id is None:
        return None

    log_dir = get_hook_log_dir(log.session_id, log.hook_id, repo_root)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp-based filename for ordering
    timestamp = log.started_at.replace(":", "-").replace(".", "-")
    log_file = log_dir / f"{timestamp}.json"

    # Convert to dict, handling enum serialization
    log_dict = asdict(log)
    log_dict["exit_status"] = log.exit_status.value

    log_file.write_text(json.dumps(log_dict, indent=2), encoding="utf-8")
    return log_file


def read_hook_log(log_path: Path) -> HookExecutionLog | None:
    """Read a hook log from a JSON file.

    Args:
        log_path: Path to the JSON log file

    Returns:
        HookExecutionLog, or None if file is invalid
    """
    if not log_path.exists():
        return None

    content = log_path.read_text(encoding="utf-8")
    data = json.loads(content)

    # Convert exit_status string back to enum
    exit_status_str = data.get("exit_status", "error")
    exit_status = HookExitStatus(exit_status_str)

    return HookExecutionLog(
        kit_id=data["kit_id"],
        hook_id=data["hook_id"],
        session_id=data.get("session_id"),
        started_at=data["started_at"],
        ended_at=data["ended_at"],
        duration_ms=data["duration_ms"],
        exit_code=data["exit_code"],
        exit_status=exit_status,
        stdout=data["stdout"],
        stderr=data["stderr"],
        stdin_context=data["stdin_context"],
        error_message=data.get("error_message"),
    )


def read_recent_hook_logs(repo_root: Path, max_age_hours: int = 24) -> list[HookExecutionLog]:
    """Read all hook logs from the last N hours.

    Scans .erk/scratch/sessions/*/hooks/*/*.json for log files.

    Args:
        repo_root: Repository root path
        max_age_hours: Maximum age of logs to include (default 24)

    Returns:
        List of HookExecutionLog sorted by started_at (newest first)
    """
    sessions_dir = repo_root / ".erk" / "scratch" / "sessions"
    if not sessions_dir.exists():
        return []

    cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
    logs: list[HookExecutionLog] = []

    # Walk session directories
    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue

        hooks_dir = session_dir / "hooks"
        if not hooks_dir.exists():
            continue

        # Walk hook directories within session
        for hook_dir in hooks_dir.iterdir():
            if not hook_dir.is_dir():
                continue

            # Read all JSON log files
            for log_file in hook_dir.glob("*.json"):
                # Quick mtime check before parsing
                if log_file.stat().st_mtime < cutoff_time:
                    continue

                log = read_hook_log(log_file)
                if log is not None:
                    logs.append(log)

    # Sort by started_at descending (newest first)
    logs.sort(key=lambda x: x.started_at, reverse=True)
    return logs


def truncate_string(s: str, max_bytes: int) -> str:
    """Truncate a string to fit within max_bytes when UTF-8 encoded.

    Args:
        s: String to truncate
        max_bytes: Maximum byte size

    Returns:
        Truncated string with "[truncated]" suffix if truncated
    """
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s

    # Binary search for safe truncation point
    # (Avoid cutting in the middle of a multi-byte character)
    truncated = encoded[: max_bytes - 12]  # Leave room for "[truncated]"
    # Decode, ignoring errors at the end
    decoded = truncated.decode("utf-8", errors="ignore")
    return decoded + "[truncated]"


def clear_hook_logs(repo_root: Path) -> int:
    """Clear all hook execution logs.

    Removes all JSON log files from .erk/scratch/sessions/*/hooks/*/.
    Also removes empty hook directories after clearing.

    Args:
        repo_root: Repository root path

    Returns:
        Number of log files deleted
    """
    sessions_dir = repo_root / ".erk" / "scratch" / "sessions"
    if not sessions_dir.exists():
        return 0

    deleted_count = 0

    # Walk session directories
    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue

        hooks_dir = session_dir / "hooks"
        if not hooks_dir.exists():
            continue

        # Walk hook directories within session
        for hook_dir in hooks_dir.iterdir():
            if not hook_dir.is_dir():
                continue

            # Delete all JSON log files
            for log_file in hook_dir.glob("*.json"):
                log_file.unlink()
                deleted_count += 1

            # Remove empty hook directory
            if not any(hook_dir.iterdir()):
                hook_dir.rmdir()

        # Remove empty hooks directory
        if not any(hooks_dir.iterdir()):
            hooks_dir.rmdir()

    return deleted_count
