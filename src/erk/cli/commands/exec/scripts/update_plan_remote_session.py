"""Update plan-header metadata with remote session artifact location.

This exec command updates the plan-header metadata block in a GitHub issue
with the remote implementation session information (run ID, session ID, timestamp).
This is called from CI after uploading the session artifact.

Usage:
    erk exec update-plan-remote-session --issue-number 123 --run-id 12345 --session-id abc

Output:
    JSON with success status or error information

Exit Codes:
    0: Success or graceful failure (to support || true pattern)
    1: Missing required arguments

Examples:
    $ erk exec update-plan-remote-session --issue-number 123 --run-id 12345 \\
        --session-id test-session
    {"success": true, "issue_number": 123}

    $ erk exec update-plan-remote-session --issue-number 999 --run-id 12345 --session-id test
    {"success": false, "error_type": "issue-not-found", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root, require_time


@dataclass(frozen=True)
class UpdateSuccess:
    """Success response for update plan remote session."""

    success: bool
    issue_number: int


@dataclass(frozen=True)
class UpdateError:
    """Error response for update plan remote session."""

    success: bool
    error_type: str
    message: str


def _output_error(error_type: str, message: str) -> None:
    """Output error JSON and exit gracefully."""
    result = UpdateError(
        success=False,
        error_type=error_type,
        message=message,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


@click.command(name="update-plan-remote-session")
@click.option(
    "--issue-number",
    required=True,
    type=int,
    help="GitHub issue number to update",
)
@click.option(
    "--run-id",
    required=True,
    type=str,
    help="GitHub Actions run ID",
)
@click.option(
    "--session-id",
    required=True,
    type=str,
    help="Claude Code session ID",
)
@click.pass_context
def update_plan_remote_session(
    ctx: click.Context,
    *,
    issue_number: int,
    run_id: str,
    session_id: str,
) -> None:
    """Update plan-header metadata with remote session artifact location.

    Updates the plan-header block in a GitHub issue with:
    - last_remote_impl_at (current timestamp)
    - last_remote_impl_run_id (GitHub Actions run ID)
    - last_remote_impl_session_id (Claude Code session ID)

    This enables the learn workflow to later retrieve the session artifact.

    Gracefully fails with exit code 0 to support || true pattern in CI.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    time = require_time(ctx)
    backend = require_plan_backend(ctx)

    # Generate timestamp
    timestamp = time.now().replace(tzinfo=UTC).isoformat()

    # Build metadata dict
    plan_id = str(issue_number)
    metadata: dict[str, object] = {
        "last_remote_impl_at": timestamp,
        "last_remote_impl_run_id": run_id,
        "last_remote_impl_session_id": session_id,
    }

    # Update metadata via PlanBackend
    try:
        backend.update_metadata(repo_root, plan_id, metadata)
    except RuntimeError as e:
        error_msg = str(e)
        if "plan-header" in error_msg.lower():
            _output_error("no-plan-header-block", error_msg)
        elif f"Issue #{issue_number} not found" in error_msg:
            _output_error("issue-not-found", f"Issue #{issue_number} not found")
        else:
            _output_error("github-api-failed", f"Failed to update metadata: {e}")
        return  # Never reached, but helps type checker

    result_success = UpdateSuccess(
        success=True,
        issue_number=issue_number,
    )
    click.echo(json.dumps(asdict(result_success), indent=2))
