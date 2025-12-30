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

from erk.kits.context_helpers import require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.github.metadata import update_plan_header_dispatch


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
    ctx: click.Context,
    issue_number: int,
    run_id: str,
    node_id: str,
    dispatched_at: str,
) -> None:
    """Update dispatch info in GitHub issue plan-header metadata.

    Fetches the issue, updates the plan-header block with last_dispatched_run_id,
    last_dispatched_node_id, and last_dispatched_at, and posts the updated body
    back to GitHub.

    If issue uses old format (no plan-header block), exits with error code 1.
    """
    # Get dependencies from context
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue
    try:
        issue = github_issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    # Update dispatch info
    try:
        updated_body = update_plan_header_dispatch(
            issue_body=issue.body,
            run_id=run_id,
            node_id=node_id,
            dispatched_at=dispatched_at,
        )
    except ValueError as e:
        # plan-header block not found (old format issue)
        result = UpdateError(
            success=False,
            error="no_plan_header_block",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    # Update issue body
    try:
        github_issues.update_issue_body(repo_root, issue_number, updated_body)
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="github_api_failed",
            message=f"Failed to update issue body: {e}",
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
