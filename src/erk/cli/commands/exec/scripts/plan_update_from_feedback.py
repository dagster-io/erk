"""Update a plan issue's plan-body comment with new content.

Usage:
    erk exec plan-update-from-feedback <issue-number> --plan-path PATH
    erk exec plan-update-from-feedback <issue-number> --plan-content "..."

Output:
    JSON with success status, issue number, comment ID, and comment URL

Exit Codes:
    0: Success
    1: Error (issue not found, missing label, no plan comment ID, or comment not found)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_comment_id,
    format_plan_content_comment,
)


@dataclass(frozen=True)
class PlanUpdateFromFeedbackSuccess:
    """Success response for plan update from feedback."""

    success: bool
    issue_number: int
    comment_id: int
    comment_url: str


@dataclass(frozen=True)
class PlanUpdateFromFeedbackError:
    """Error response for plan update from feedback."""

    success: bool
    error: str
    message: str


class PlanUpdateFromFeedbackException(Exception):
    """Exception raised during plan update from feedback."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def _update_plan_from_feedback_impl(
    github_issues: GitHubIssues,
    *,
    repo_root: Path,
    issue_number: int,
    plan_content: str,
) -> PlanUpdateFromFeedbackSuccess:
    """Update the plan-body comment on a plan issue.

    Args:
        github_issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Issue number to update
        plan_content: New plan markdown content

    Returns:
        PlanUpdateFromFeedbackSuccess on success

    Raises:
        PlanUpdateFromFeedbackException: If validation fails
    """
    # LBYL: Check if issue exists
    if not github_issues.issue_exists(repo_root, issue_number):
        raise PlanUpdateFromFeedbackException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    issue = github_issues.get_issue(repo_root, issue_number)

    # Validate erk-plan label
    if "erk-plan" not in issue.labels:
        raise PlanUpdateFromFeedbackException(
            error="missing_erk_plan_label",
            message=f"Issue #{issue_number} does not have the erk-plan label",
        )

    # Extract plan_comment_id from metadata
    plan_comment_id = extract_plan_header_comment_id(issue.body)
    if plan_comment_id is None:
        raise PlanUpdateFromFeedbackException(
            error="no_plan_comment_id",
            message=f"Issue #{issue_number} has no plan_comment_id in metadata",
        )

    # Fetch comments and find matching one
    comments = github_issues.get_issue_comments_with_urls(repo_root, issue_number)

    matching_comment = None
    for comment in comments:
        if comment.id == plan_comment_id:
            matching_comment = comment
            break

    if matching_comment is None:
        raise PlanUpdateFromFeedbackException(
            error="comment_not_found",
            message=f"Comment {plan_comment_id} not found on issue #{issue_number}",
        )

    # Format and update the comment
    formatted_body = format_plan_content_comment(plan_content)
    github_issues.update_comment(repo_root, plan_comment_id, formatted_body)

    return PlanUpdateFromFeedbackSuccess(
        success=True,
        issue_number=issue_number,
        comment_id=plan_comment_id,
        comment_url=matching_comment.url,
    )


@click.command(name="plan-update-from-feedback")
@click.argument("issue_number", type=int)
@click.option("--plan-path", type=click.Path(exists=True), help="Path to plan markdown file")
@click.option("--plan-content", type=str, help="Plan content as string")
@click.pass_context
def plan_update_from_feedback(
    ctx: click.Context,
    issue_number: int,
    plan_path: str | None,
    plan_content: str | None,
) -> None:
    """Update a plan issue's plan-body comment with new content.

    Requires exactly one of --plan-path or --plan-content.
    """
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Validate mutually exclusive options
    if plan_path is not None and plan_content is not None:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Cannot specify both --plan-path and --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    if plan_path is None and plan_content is None:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Must specify either --plan-path or --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    # Read content from file or use provided string
    # Both-None and both-set cases already handled above with early return
    if plan_path is not None:
        content = Path(plan_path).read_text(encoding="utf-8")
    elif plan_content is not None:
        content = plan_content
    else:
        # Unreachable: guarded by validation above, but satisfies type checker
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Must specify either --plan-path or --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    try:
        result = _update_plan_from_feedback_impl(
            github_issues,
            repo_root=repo_root,
            issue_number=issue_number,
            plan_content=content,
        )
        click.echo(json.dumps(asdict(result)))
    except PlanUpdateFromFeedbackException as e:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error=e.error,
            message=e.message,
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1) from None
