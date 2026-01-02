"""Marker file operations for inter-process communication.

Usage:
    erk exec marker create <name>
    erk exec marker exists <name>
    erk exec marker delete <name>

Marker files are stored in `.erk/scratch/sessions/<session-id>/` and are used for
inter-process communication between hooks and commands. Session ID is obtained
from `$CLAUDE_CODE_SESSION_ID` environment variable.

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


def _get_session_id() -> str | None:
    """Get session ID from environment variable."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID")


def _output_json(success: bool, message: str) -> None:
    """Output JSON response."""
    click.echo(json.dumps({"success": success, "message": message}))


@click.group(name="marker")
def marker() -> None:
    """Manage marker files for inter-process communication."""


@marker.command(name="create")
@click.argument("name")
@click.pass_context
def marker_create(ctx: click.Context, name: str) -> None:
    """Create a marker file.

    NAME is the marker name (e.g., 'incremental-plan').
    The '.marker' extension is added automatically.
    """
    session_id = _get_session_id()
    if session_id is None:
        _output_json(False, "Missing CLAUDE_CODE_SESSION_ID environment variable")
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"
    marker_file.touch()
    _output_json(True, f"Created marker: {name}")


@marker.command(name="exists")
@click.argument("name")
@click.pass_context
def marker_exists(ctx: click.Context, name: str) -> None:
    """Check if a marker file exists.

    NAME is the marker name (e.g., 'incremental-plan').
    Exit code 0 if exists, 1 if not.
    """
    session_id = _get_session_id()
    if session_id is None:
        _output_json(False, "Missing CLAUDE_CODE_SESSION_ID environment variable")
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"

    if marker_file.exists():
        _output_json(True, f"Marker exists: {name}")
    else:
        _output_json(False, f"Marker does not exist: {name}")
        raise SystemExit(1) from None


@marker.command(name="delete")
@click.argument("name")
@click.pass_context
def marker_delete(ctx: click.Context, name: str) -> None:
    """Delete a marker file.

    NAME is the marker name (e.g., 'incremental-plan').
    Succeeds even if marker doesn't exist (idempotent).
    """
    session_id = _get_session_id()
    if session_id is None:
        _output_json(False, "Missing CLAUDE_CODE_SESSION_ID environment variable")
        raise SystemExit(1) from None

    repo_root = require_repo_root(ctx)
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"{name}{MARKER_EXTENSION}"

    if marker_file.exists():
        marker_file.unlink()
        _output_json(True, f"Deleted marker: {name}")
    else:
        _output_json(True, f"Marker already deleted: {name}")
