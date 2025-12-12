"""Data types for hook execution logging."""

from dataclasses import dataclass
from enum import Enum


class HookExitStatus(Enum):
    """Classification of hook exit status."""

    SUCCESS = "success"  # Exit code 0
    BLOCKED = "blocked"  # Exit code 2 (blocks the action)
    ERROR = "error"  # Other exit codes
    EXCEPTION = "exception"  # Uncaught exception in hook code


@dataclass(frozen=True)
class HookExecutionLog:
    """Record of a single hook execution.

    Attributes:
        kit_id: Kit that owns the hook (e.g., "erk", "devrun")
        hook_id: Hook identifier (e.g., "session-id-injector-hook")
        session_id: Claude Code session ID, if available
        started_at: ISO 8601 timestamp when hook started
        ended_at: ISO 8601 timestamp when hook ended
        duration_ms: Execution time in milliseconds
        exit_code: Process exit code
        exit_status: Classified exit status
        stdout: Captured stdout (truncated to 10KB)
        stderr: Captured stderr (truncated to 10KB)
        stdin_context: Input context JSON (truncated to 2KB)
        error_message: Exception message if exit_status is EXCEPTION
    """

    kit_id: str
    hook_id: str
    session_id: str | None
    started_at: str
    ended_at: str
    duration_ms: int
    exit_code: int
    exit_status: HookExitStatus
    stdout: str
    stderr: str
    stdin_context: str
    error_message: str | None = None


def classify_exit_code(exit_code: int) -> HookExitStatus:
    """Classify an exit code into a HookExitStatus.

    Args:
        exit_code: Process exit code

    Returns:
        HookExitStatus based on convention:
        - 0: SUCCESS (hook ran without issues)
        - 2: BLOCKED (hook blocked the action)
        - Other: ERROR (unexpected failure)
    """
    if exit_code == 0:
        return HookExitStatus.SUCCESS
    if exit_code == 2:
        return HookExitStatus.BLOCKED
    return HookExitStatus.ERROR
