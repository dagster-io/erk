"""Create scratch directory and optional marker file.

This kit CLI command creates the .erk/scratch/<session-id>/ directory
(idempotent) and optionally creates a marker file within it.

This pushes down the raw bash instructions from exit_plan_mode_hook.py
to a proper kit CLI command following the predicate push-down pattern.

Usage:
    dot-agent run erk touch-scratch-marker --session-id <id>
    dot-agent run erk touch-scratch-marker --session-id <id> --marker skip-plan-save

Output:
    JSON with scratch_dir path and optional marker_path

Exit Codes:
    0: Success
    1: Error (not in git repo or other failure)

Examples:
    $ dot-agent run erk touch-scratch-marker --session-id abc123 --marker skip-plan-save
    {"success": true, "scratch_dir": ".erk/scratch/abc123",
     "marker_path": ".erk/scratch/abc123/skip-plan-save"}

    $ dot-agent run erk touch-scratch-marker --session-id abc123
    {"success": true, "scratch_dir": ".erk/scratch/abc123", "marker_path": null}
"""

import json
from pathlib import Path
from typing import NoReturn

import click
from erk_shared.scratch.scratch import get_scratch_dir


def _error(msg: str, details: str | None = None) -> NoReturn:
    """Output error message as JSON and exit with code 1.

    Args:
        msg: Error message
        details: Optional additional details
    """
    error_obj = {"success": False, "error": msg}
    if details:
        error_obj["details"] = details
    click.echo(json.dumps(error_obj))
    raise SystemExit(1)


@click.command(name="touch-scratch-marker")
@click.option("--session-id", required=True, help="Claude session ID")
@click.option("--marker", default=None, help="Marker filename to create (optional)")
def touch_scratch_marker(session_id: str, marker: str | None) -> None:
    """Create scratch directory and optional marker file.

    Creates .erk/scratch/<session-id>/ directory (idempotent) and optionally
    creates a marker file within it.

    Output: JSON with scratch_dir path and optional marker_path.
    """
    # Validate session_id is not empty
    if not session_id:
        _error("session_id cannot be empty")

    # Create scratch directory (idempotent)
    try:
        scratch_dir = get_scratch_dir(session_id)
    except Exception as e:
        _error("Failed to create scratch directory", details=str(e))

    marker_path: Path | None = None

    # Create marker file if requested
    if marker:
        marker_path = scratch_dir / marker
        try:
            marker_path.touch()
        except Exception as e:
            _error(f"Failed to create marker file: {marker}", details=str(e))

    # Output JSON result
    result = {
        "success": True,
        "scratch_dir": str(scratch_dir),
        "marker_path": str(marker_path) if marker_path else None,
    }
    click.echo(json.dumps(result))
