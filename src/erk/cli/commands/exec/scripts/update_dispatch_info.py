"""Update dispatch info in GitHub issue plan-header metadata.

Usage:
    erk exec update-dispatch-info <issue-number> <run-id> <node-id> <dispatched-at>

Output:
    JSON with success status and issue_number

Exit Codes:
    0: Success
    1: Error (issue not found, invalid inputs, no plan-header block)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root


@dataclass(frozen=True)
class UpdateSuccess:
    """Success response for dispatch info update."""

    success: bool
    issue_number: int
    run_id: str
    node_id: str


@dataclass(frozen=True)
class UpdateError:
    """Error response for dispatch info update."""

    success: bool
    error: str
    message: str


@click.command(name="update-dispatch-info")
@click.argument("issue_number", type=int)
@click.argument("run_id")
@click.argument("node_id")
@click.argument("dispatched_at")
@click.pass_context
def update_dispatch_info(
    ctx: click.Context, *, issue_number: int, run_id: str, node_id: str, dispatched_at: str
) -> None:
    """Update dispatch info in GitHub issue plan-header metadata.

    Updates the plan-header block with last_dispatched_run_id,
    last_dispatched_node_id, and last_dispatched_at via PlanBackend.

    If issue uses old format (no plan-header block), exits with error code 1.
    """
    # Get dependencies from context
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    # Update dispatch info metadata directly via PlanBackend
    try:
        backend.update_metadata(
            repo_root,
            str(issue_number),
            metadata={
                "last_dispatched_run_id": run_id,
                "last_dispatched_node_id": node_id,
                "last_dispatched_at": dispatched_at,
            },
        )
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="github-api-failed",
            message=f"Failed to update dispatch info: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    result_success = UpdateSuccess(
        success=True,
        issue_number=issue_number,
        run_id=run_id,
        node_id=node_id,
    )
    click.echo(json.dumps(asdict(result_success)))
