"""Update objective_issue in GitHub issue plan-header metadata.

Usage:
    erk exec update-plan-objective <plan-issue-number> <objective-issue-number>

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
    """Success response for plan objective update."""

    success: bool
    issue_number: int
    objective_issue: int


@dataclass(frozen=True)
class UpdateError:
    """Error response for plan objective update."""

    success: bool
    error: str
    message: str


@click.command(name="update-plan-objective")
@click.argument("plan_issue_number", type=int)
@click.argument("objective_issue_number", type=int)
@click.pass_context
def update_plan_objective(
    ctx: click.Context, *, plan_issue_number: int, objective_issue_number: int
) -> None:
    """Update objective_issue in GitHub issue plan-header metadata.

    Sets the objective_issue field in the plan-header block via PlanBackend.

    If issue uses old format (no plan-header block), exits with error code 1.
    """
    if objective_issue_number <= 0:
        result = UpdateError(
            success=False,
            error="invalid-input",
            message=f"objective_issue_number must be positive, got {objective_issue_number}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    try:
        backend.update_metadata(
            repo_root,
            str(plan_issue_number),
            metadata={"objective_issue": objective_issue_number},
        )
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="github-api-failed",
            message=f"Failed to update plan objective: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    result_success = UpdateSuccess(
        success=True,
        issue_number=plan_issue_number,
        objective_issue=objective_issue_number,
    )
    click.echo(json.dumps(asdict(result_success)))
