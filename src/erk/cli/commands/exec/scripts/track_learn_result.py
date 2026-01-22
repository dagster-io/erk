"""Track learn workflow result on a plan issue.

This exec script updates the plan-header metadata block to record the result
of a learn workflow. It sets the learn_status field and optionally records
the learn_plan_issue if a plan was created.

Usage:
    erk exec track-learn-result --issue 123 --status completed_no_plan
    erk exec track-learn-result --issue 123 --status completed_with_plan --plan-issue 456

Output:
    JSON object with tracking result:
    {
        "success": true,
        "issue_number": 123,
        "learn_status": "completed_no_plan"
    }

Exit Codes:
    0: Success
    1: Error (invalid issue, GitHub failure, validation error, etc.)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.github.metadata.plan_header import update_plan_header_learn_result
from erk_shared.github.metadata.schemas import LearnStatusValue


@dataclass(frozen=True)
class TrackLearnResultSuccess:
    """Result of successful track-learn-result command."""

    success: bool
    issue_number: int
    learn_status: str
    learn_plan_issue: int | None
    learn_plan_pr: int | None


@dataclass(frozen=True)
class TrackLearnResultError:
    """Error result when tracking fails."""

    success: bool
    error: str


# Valid status values for learn result
VALID_RESULT_STATUSES: set[LearnStatusValue] = {
    "completed_no_plan",
    "completed_with_plan",
    "pending_review",
}


@click.command(name="track-learn-result")
@click.option(
    "--issue",
    required=True,
    type=int,
    help="Parent plan issue number",
)
@click.option(
    "--status",
    required=True,
    type=click.Choice(["completed_no_plan", "completed_with_plan", "pending_review"]),
    help="Learn workflow result status",
)
@click.option(
    "--plan-issue",
    type=int,
    help="Learn plan issue number (required if status is completed_with_plan)",
)
@click.option(
    "--plan-pr",
    type=int,
    help="Learn documentation PR number (required if status is pending_review)",
)
@click.pass_context
def track_learn_result(
    ctx: click.Context,
    *,
    issue: int,
    status: str,
    plan_issue: int | None,
    plan_pr: int | None,
) -> None:
    """Track learn workflow result on a plan issue.

    Updates the plan-header metadata block with the learn workflow result.
    If status is 'completed_with_plan', also records the learn_plan_issue.
    If status is 'pending_review', also records the learn_plan_pr.
    """
    # Validate: completed_with_plan requires --plan-issue
    if status == "completed_with_plan" and plan_issue is None:
        error = TrackLearnResultError(
            success=False,
            error="--plan-issue is required when status is 'completed_with_plan'",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # completed_no_plan should not have --plan-issue
    if status == "completed_no_plan" and plan_issue is not None:
        error = TrackLearnResultError(
            success=False,
            error="--plan-issue should not be provided when status is 'completed_no_plan'",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Validate: pending_review requires --plan-pr
    if status == "pending_review" and plan_pr is None:
        error = TrackLearnResultError(
            success=False,
            error="--plan-pr is required when status is 'pending_review'",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # pending_review should not have --plan-issue
    if status == "pending_review" and plan_issue is not None:
        error = TrackLearnResultError(
            success=False,
            error="--plan-issue should not be provided when status is 'pending_review'",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # completed_with_plan should not have --plan-pr
    if status == "completed_with_plan" and plan_pr is not None:
        error = TrackLearnResultError(
            success=False,
            error="--plan-pr should not be provided when status is 'completed_with_plan'",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Get dependencies from context
    github_issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue body
    issue_info = github_issues.get_issue(repo_root, issue)

    # Cast status to LearnStatusValue (already validated by click.Choice)
    learn_status: LearnStatusValue = status  # type: ignore[assignment]

    # Update plan-header with learn result
    updated_body = update_plan_header_learn_result(
        issue_body=issue_info.body,
        learn_status=learn_status,
        learn_plan_issue=plan_issue,
        learn_plan_pr=plan_pr,
    )

    # Update issue
    github_issues.update_issue_body(repo_root, issue, updated_body)

    result = TrackLearnResultSuccess(
        success=True,
        issue_number=issue,
        learn_status=status,
        learn_plan_issue=plan_issue,
        learn_plan_pr=plan_pr,
    )

    click.echo(json.dumps(asdict(result), indent=2))
