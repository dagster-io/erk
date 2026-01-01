"""Decorators for hook commands."""

import functools
import io
import json
import os
import sys
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from typing import TypeVar

from erk_shared.hooks.logging import (
    MAX_STDERR_BYTES,
    MAX_STDIN_BYTES,
    MAX_STDOUT_BYTES,
    truncate_string,
    write_hook_log,
)
from erk_shared.hooks.types import HookExecutionLog, HookExitStatus, classify_exit_code

F = TypeVar("F", bound=Callable[..., None])


def _read_stdin_once() -> str:
    """Read stdin if available, returning empty string if not.

    This is a one-time read - stdin cannot be read again after this.
    """
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def _extract_session_id(stdin_data: str) -> str | None:
    """Extract session_id from stdin JSON if present.

    Args:
        stdin_data: Raw stdin content

    Returns:
        session_id if found in JSON, None otherwise
    """
    if not stdin_data.strip():
        return None
    data = json.loads(stdin_data)
    return data.get("session_id")


def logged_hook(func: F) -> F:
    """Decorator that logs hook execution for health monitoring.

    This decorator MUST be applied BEFORE @project_scoped so that logging
    happens even when the hook exits early due to project scope.

    The decorator:
    1. Reads ERK_HOOK_ID from environment
    2. Captures stdin (contains session_id in JSON from Claude Code)
    3. Redirects stdout/stderr to capture output
    4. Records timing and exit status
    5. Writes log on exit (success or failure)
    6. Re-emits captured output to real stdout/stderr

    Environment variables:
        ERK_HOOK_ID: Hook identifier (e.g., "session-id-injector-hook")

    Usage:
        @click.command()
        @logged_hook
        @project_scoped
        def my_hook() -> None:
            click.echo("Hook output")
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Read environment variables
        hook_id = os.environ.get("ERK_HOOK_ID", "unknown")

        # Capture stdin before hook reads it
        stdin_data = _read_stdin_once()
        session_id: str | None = None
        try:
            session_id = _extract_session_id(stdin_data)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Replace stdin with a StringIO containing the captured data
        # so the hook can still read it
        original_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin_data)

        # Capture stdout/stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        # Record start time
        started_at = datetime.now(UTC)
        exit_code = 0
        exit_status = HookExitStatus.SUCCESS
        error_message: str | None = None

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                func(*args, **kwargs)
        except SystemExit as e:
            # Click raises SystemExit on exit
            exit_code = e.code if isinstance(e.code, int) else 1
            exit_status = classify_exit_code(exit_code)
        except Exception as e:
            # Uncaught exception
            exit_code = 1
            exit_status = HookExitStatus.EXCEPTION
            error_message = f"{type(e).__name__}: {e}"
            # Write traceback to stderr buffer
            stderr_buffer.write(traceback.format_exc())
        finally:
            # Restore stdin
            sys.stdin = original_stdin

            # Record end time
            ended_at = datetime.now(UTC)
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)

            # Get captured output
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()

            # Create log entry
            log = HookExecutionLog(
                kit_id="erk",  # All hooks are now in erk
                hook_id=hook_id,
                session_id=session_id,
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
                duration_ms=duration_ms,
                exit_code=exit_code,
                exit_status=exit_status,
                stdout=truncate_string(stdout_content, MAX_STDOUT_BYTES),
                stderr=truncate_string(stderr_content, MAX_STDERR_BYTES),
                stdin_context=truncate_string(stdin_data, MAX_STDIN_BYTES),
                error_message=error_message,
            )

            # Write log (only if we have a session_id)
            write_hook_log(log)

            # Re-emit captured output
            sys.stdout.write(stdout_content)
            sys.stderr.write(stderr_content)

        # Re-raise SystemExit if hook exited with non-zero
        if exit_code != 0:
            raise SystemExit(exit_code)

    return wrapper  # type: ignore[return-value]
