"""Close a plan review PR without merging.

Usage:
    erk exec plan-review-complete <issue-number>

Output:
    JSON with success status, issue number, and PR number

Exit Codes:
    0: Success
    1: Error (issue not found, no plan header, or no review PR)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_github,
    require_repo_root,
)
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_review_pr


@dataclass(frozen=True)
class PlanReviewCompleteSuccess:
    """Success response for plan review PR completion."""

    success: bool
    issue_number: int
    pr_number: int


@dataclass(frozen=True)
class PlanReviewCompleteError:
    """Error response for plan review PR completion."""

    success: bool
    error: str
    message: str


class PlanReviewCompleteException(Exception):
    """Exception raised during plan review PR completion."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def _plan_review_complete_impl(
    github: GitHub,
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> PlanReviewCompleteSuccess:
    """Close a plan review PR without merging.

    Args:
        github: GitHub gateway
        github_issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Plan issue number

    Returns:
        PlanReviewCompleteSuccess on success

    Raises:
        PlanReviewCompleteException: If issue not found, no plan header, or no review PR
    """
    # LBYL: Check if issue exists
    if not github_issues.issue_exists(repo_root, issue_number):
        raise PlanReviewCompleteException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    # LBYL: Extract review_pr from plan-header
    issue = github_issues.get_issue(repo_root, issue_number)

    try:
        review_pr = extract_plan_header_review_pr(issue.body)
    except ValueError:
        raise PlanReviewCompleteException(
            error="no_plan_header",
            message=f"Issue #{issue_number} is missing plan-header metadata block",
        ) from None

    # LBYL: Check review_pr is not None
    if review_pr is None:
        raise PlanReviewCompleteException(
            error="no_review_pr",
            message=f"Issue #{issue_number} has no active review PR",
        )

    # Close the PR
    github.close_pr(repo_root, review_pr)

    return PlanReviewCompleteSuccess(
        success=True,
        issue_number=issue_number,
        pr_number=review_pr,
    )


@click.command(name="plan-review-complete")
@click.argument("issue_number", type=int)
@click.pass_context
def plan_review_complete(
    ctx: click.Context,
    issue_number: int,
) -> None:
    """Close a plan review PR without merging.

    Looks up the review_pr from plan-header metadata and closes it.
    """
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    try:
        result = _plan_review_complete_impl(
            github,
            github_issues=github.issues,
            repo_root=repo_root,
            issue_number=issue_number,
        )
        click.echo(json.dumps(asdict(result)))
    except PlanReviewCompleteException as e:
        error_response = PlanReviewCompleteError(
            success=False,
            error=e.error,
            message=e.message,
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1) from None
