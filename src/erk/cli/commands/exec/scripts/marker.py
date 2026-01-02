"""Marker file operations for inter-process communication.

Usage:
    erk exec marker create --session-id SESSION_ID <name>
    erk exec marker exists --session-id SESSION_ID <name>
    erk exec marker delete --session-id SESSION_ID <name>

Marker files are stored in `.erk/scratch/sessions/<session-id>/` and are used for
inter-process communication between hooks and commands. Session ID can be provided
via `--session-id` flag or `$CLAUDE_CODE_SESSION_ID` environment variable.

The `--session-id` flag takes precedence over the environment variable.

Exit codes:
    create: 0 = created, 1 = error (missing session ID)
    exists: 0 = exists, 1 = does not exist
    delete: 0 = deleted (or didn't exist), 1 = error (missing session ID)
"""

import json
import os

import click

from erk_shared.context.helpers import require_repo_root
from erk_shared.scratch.scratch import get_scratch_dir

MARKER_EXTENSION = ".marker"


def _resolve_session_id(session_id: str | None) -> str | None:
    """Resolve session ID from explicit argument or environment variable.

    Priority:
    1. Explicit session_id argument (if provided)
    2. CLAUDE_CODE_SESSION_ID environment variable
    3. None (if neither available)
    """
    if session_id is not None:
        return session_id
    return os.environ.get("CLAUDE_CODE_SESSION_ID")


def _output_json(success: bool, message: str) -> None:
    """Output JSON response."""
    click.echo(json.dumps({"success": success, "message": message}))


@click.group(name="marker")
def marker() -> None:
    """Manage marker files for inter-process communication."""


@marker.command(name="create")
@click.argument("name")
@click.option(
    "--session-id",
    default=None,
    help="Session ID for marker storage (default: $CLAUDE_CODE_SESSION_ID)",
)
@click.pass_context
def marker_create(ctx: click.Context, name: str, session_id: str | None) -> None:
    """Create a marker file.

    NAME is the marker name (e.g., 'incremental-plan').
    The '.marker' extension is added automatically.
    """
    resolved_session_id = _resolve_session_id(session_id)
    if resolved_session_id is None:
        msg = (
            "Missing session ID: provide --session-id or set "
            "CLAUDE_CODE_SESSION_ID environment variable"
        )
        _output_json(False, msg)
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(resolved_session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"
    marker_file.touch()
    _output_json(True, f"Created marker: {name}")


@marker.command(name="exists")
@click.argument("name")
@click.option(
    "--session-id",
    default=None,
    help="Session ID for marker storage (default: $CLAUDE_CODE_SESSION_ID)",
)
@click.pass_context
def marker_exists(ctx: click.Context, name: str, session_id: str | None) -> None:
    """Check if a marker file exists.

    NAME is the marker name (e.g., 'incremental-plan').
    Exit code 0 if exists, 1 if not.
    """
    resolved_session_id = _resolve_session_id(session_id)
    if resolved_session_id is None:
        msg = (
            "Missing session ID: provide --session-id or set "
            "CLAUDE_CODE_SESSION_ID environment variable"
        )
        _output_json(False, msg)
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(resolved_session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"

    if marker_file.exists():
        _output_json(True, f"Marker exists: {name}")
    else:
        _output_json(False, f"Marker does not exist: {name}")
        raise SystemExit(1) from None


@marker.command(name="delete")
@click.argument("name")
@click.option(
    "--session-id",
    default=None,
    help="Session ID for marker storage (default: $CLAUDE_CODE_SESSION_ID)",
)
@click.pass_context
def marker_delete(ctx: click.Context, name: str, session_id: str | None) -> None:
    """Delete a marker file.

    NAME is the marker name (e.g., 'incremental-plan').
    Succeeds even if marker doesn't exist (idempotent).
    """
    resolved_session_id = _resolve_session_id(session_id)
    if resolved_session_id is None:
        msg = (
            "Missing session ID: provide --session-id or set "
            "CLAUDE_CODE_SESSION_ID environment variable"
        )
        _output_json(False, msg)
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(resolved_session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"

    if marker_file.exists():
        marker_file.unlink()
        _output_json(True, f"Deleted marker: {name}")
    else:
        _output_json(True, f"Marker already deleted: {name}")
