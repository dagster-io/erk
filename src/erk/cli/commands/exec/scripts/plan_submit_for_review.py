"""Fetch plan content from a GitHub issue for PR-based review workflow.

Usage:
    erk exec plan-submit-for-review <issue-number>

Output:
    JSON with plan content and metadata

Exit Codes:
    0: Success
    1: Error (issue not found, missing erk-plan label, or no plan content)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
)


@dataclass(frozen=True)
class PlanSubmitSuccess:
    """Success response for plan submission."""

    success: bool
    issue_number: int
    title: str
    url: str
    plan_content: str
    plan_comment_id: int
    plan_comment_url: str


@dataclass(frozen=True)
class PlanSubmitError:
    """Error response for plan submission."""

    success: bool
    error: str
    message: str


@click.command(name="plan-submit-for-review")
@click.argument("issue_number", type=int)
@click.pass_context
def plan_submit_for_review(
    ctx: click.Context,
    issue_number: int,
) -> None:
    """Fetch plan content from a GitHub issue for PR-based review workflow.

    Validates the issue has the erk-plan label, extracts the plan content
    from the first comment, and returns all data needed for creating a
    temporary review PR.
    """
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch issue
    issue = github_issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        result = PlanSubmitError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Validate erk-plan label
    if "erk-plan" not in issue.labels:
        result = PlanSubmitError(
            success=False,
            error="missing_erk_plan_label",
            message=f"Issue #{issue_number} does not have the erk-plan label",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Extract plan comment ID from metadata
    plan_comment_id = extract_plan_header_comment_id(issue.body)
    if plan_comment_id is None:
        result = PlanSubmitError(
            success=False,
            error="no_plan_content",
            message=f"Issue #{issue_number} has no plan_comment_id in metadata",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Fetch comments with URLs
    try:
        comments = github_issues.get_issue_comments_with_urls(repo_root, issue_number)
    except RuntimeError as e:
        result = PlanSubmitError(
            success=False,
            error="no_plan_content",
            message=f"Failed to fetch comments for issue #{issue_number}: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from e

    if not comments:
        result = PlanSubmitError(
            success=False,
            error="no_plan_content",
            message=f"Issue #{issue_number} has no comments",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Find the comment with the plan content
    plan_comment_url = None
    plan_content = None

    for comment in comments:
        if comment.id == plan_comment_id:
            plan_comment_url = comment.url
            content = extract_plan_from_comment(comment.body)
            if content:
                plan_content = content
                break

    if plan_content is None or plan_comment_url is None:
        result = PlanSubmitError(
            success=False,
            error="no_plan_content",
            message=f"Issue #{issue_number} comment {plan_comment_id} has no plan markers",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Success - type checker now knows plan_comment_url is not None
    result = PlanSubmitSuccess(
        success=True,
        issue_number=issue_number,
        title=issue.title,
        url=issue.url,
        plan_content=plan_content,
        plan_comment_id=plan_comment_id,
        plan_comment_url=plan_comment_url,
    )
    click.echo(json.dumps(asdict(result)))
