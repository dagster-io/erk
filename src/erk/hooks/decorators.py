"""Decorators for hook commands."""

from __future__ import annotations

import functools
import inspect
import io
import json
import os
import sys
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    import click

from erk_shared.context.types import NoRepoSentinel
from erk_shared.hooks.logging import (
    MAX_STDERR_BYTES,
    MAX_STDIN_BYTES,
    MAX_STDOUT_BYTES,
    truncate_string,
    write_hook_log,
)
from erk_shared.hooks.types import HookExecutionLog, HookExitStatus, classify_exit_code
from erk_shared.scratch.scratch import get_scratch_dir

F = TypeVar("F", bound=Callable[..., None])


@dataclass(frozen=True)
class HookContext:
    """Context injected into hooks by the @logged_hook decorator.

    This dataclass consolidates common derived values that hooks need,
    eliminating duplicated code across hook implementations.

    Attributes:
        session_id: Claude session ID from stdin JSON, or None if not available.
        repo_root: Path to the git repository root.
        scratch_dir: Session-scoped scratch directory, or None if no session_id.
        is_erk_project: True if repo_root/.erk directory exists.
    """

    session_id: str | None
    repo_root: Path
    scratch_dir: Path | None
    is_erk_project: bool


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


def _build_hook_context(
    session_id: str | None,
    repo_root: Path,
) -> HookContext:
    """Build HookContext with derived values.

    Args:
        session_id: Claude session ID from stdin JSON, or None.
        repo_root: Path to the git repository root.

    Returns:
        HookContext with all derived values computed.
    """
    is_erk_project = (repo_root / ".erk").is_dir()

    scratch_dir: Path | None = None
    if session_id is not None:
        scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)

    return HookContext(
        session_id=session_id,
        repo_root=repo_root,
        scratch_dir=scratch_dir,
        is_erk_project=is_erk_project,
    )


def _extract_repo_root_from_click_context(args: tuple) -> Path | None:
    """Extract repo_root from Click context if available.

    Looks for ctx.obj with a repo attribute that has a root path.
    Handles NoRepoSentinel by returning None.

    Args:
        args: Positional arguments passed to the wrapped function.

    Returns:
        Path to repo root if found, None otherwise.
    """
    # First arg should be Click context if @click.pass_context was used
    if not args:
        return None

    ctx = args[0]

    # Check if it's a Click context with our ErkContext in obj
    if not hasattr(ctx, "obj"):
        return None

    obj = ctx.obj
    if obj is None:
        return None

    if not hasattr(obj, "repo"):
        return None

    repo = obj.repo
    if isinstance(repo, NoRepoSentinel):
        return None

    if not hasattr(repo, "root"):
        return None

    return repo.root


def _function_accepts_hook_ctx(func: Callable) -> bool:
    """Check if a function signature accepts hook_ctx parameter.

    Args:
        func: The function to inspect.

    Returns:
        True if function has a hook_ctx parameter.
    """
    sig = inspect.signature(func)
    return "hook_ctx" in sig.parameters


def logged_hook[F: Callable[..., None]](func: F) -> F:
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
    7. Injects HookContext if function signature accepts hook_ctx parameter

    Environment variables:
        ERK_HOOK_ID: Hook identifier (e.g., "session-id-injector-hook")

    Usage:
        @click.command()
        @click.pass_context
        @logged_hook
        def my_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
            if not hook_ctx.is_erk_project:
                return
            click.echo(f"Session: {hook_ctx.session_id}")
    """
    # Check once at decoration time whether function accepts hook_ctx
    accepts_hook_ctx = _function_accepts_hook_ctx(func)

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

        # Build HookContext if function accepts it and we can extract repo_root
        if accepts_hook_ctx:
            repo_root = _extract_repo_root_from_click_context(args)
            if repo_root is not None:
                hook_ctx = _build_hook_context(session_id, repo_root)
                kwargs["hook_ctx"] = hook_ctx

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


def hook_command(name: str | None = None) -> Callable[[Callable[..., None]], click.Command]:
    """Combined decorator for hook commands.

    This decorator combines @click.command, @click.pass_context, and @logged_hook
    into a single decorator, reducing boilerplate in hook implementations.

    Args:
        name: Optional command name. If not provided, Click will infer from function name.

    Usage:
        @hook_command(name="my-hook")
        def my_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
            if not hook_ctx.is_erk_project:
                return
            click.echo(f"Session: {hook_ctx.session_id}")

    Equivalent to:
        @click.command(name="my-hook")
        @click.pass_context
        @logged_hook
        def my_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
            ...
    """
    # Inline import to avoid circular dependency at module load time
    import click

    def decorator(func: Callable[..., None]) -> click.Command:
        # Apply decorators in reverse order (innermost first)
        # 1. @logged_hook (innermost - applied first)
        wrapped = logged_hook(func)
        # 2. @click.pass_context
        wrapped = click.pass_context(wrapped)
        # 3. @click.command (outermost - applied last)
        if name is not None:
            return click.command(name=name)(wrapped)
        return click.command()(wrapped)

    return decorator
