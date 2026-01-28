"""Create a draft PR for plan review and update plan metadata.

Usage:
    erk exec plan-create-review-pr <issue-number> <branch-name> <plan-title>

Output:
    JSON with success status, issue number, PR number, and PR URL

Exit Codes:
    0: Success
    1: Error (issue not found, PR creation failed, or metadata update failed)
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
from erk_shared.gateway.github.metadata.plan_header import update_plan_header_review_pr
from erk_shared.gateway.github.types import BodyText


@dataclass(frozen=True)
class CreateReviewPRSuccess:
    """Success response for plan review PR creation."""

    success: bool
    issue_number: int
    pr_number: int
    pr_url: str


@dataclass(frozen=True)
class CreateReviewPRError:
    """Error response for plan review PR creation."""

    success: bool
    error: str
    message: str


class CreateReviewPRException(Exception):
    """Exception raised during plan review PR creation."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def _format_pr_body(issue_number: int, plan_title: str) -> str:
    """Format PR body with link to plan issue and warning.

    Args:
        issue_number: Plan issue number
        plan_title: Title of the plan

    Returns:
        Formatted markdown PR body
    """
    return f"""# Plan Review: {plan_title}

This PR is for reviewing the plan in issue #{issue_number}.

**Plan Issue:** #{issue_number}

## Important

**This PR will not be merged.** It exists solely to enable inline review comments on the plan.

Once review is complete, the plan will be implemented directly and this PR will be closed.
"""


def _create_review_pr_impl(
    github: GitHub,
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
    branch_name: str,
    plan_title: str,
) -> CreateReviewPRSuccess:
    """Create a draft PR for plan review and update plan metadata.

    Args:
        github: GitHub gateway
        github_issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Plan issue number
        branch_name: Branch name for the PR
        plan_title: Title of the plan

    Returns:
        CreateReviewPRSuccess on success

    Raises:
        CreateReviewPRException: If issue not found or PR creation fails
    """
    # LBYL: Check if issue exists before proceeding
    if not github_issues.issue_exists(repo_root, issue_number):
        raise CreateReviewPRException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    # Create draft PR
    pr_title = f"Plan Review: {plan_title} (#{issue_number})"
    pr_body = _format_pr_body(issue_number, plan_title)

    try:
        pr_number = github.create_pr(
            repo_root,
            branch_name,
            pr_title,
            pr_body,
            base="master",
            draft=True,
        )
    except Exception as e:
        raise CreateReviewPRException(
            error="pr_creation_failed",
            message=f"Failed to create PR: {e}",
        ) from e

    # Get issue body to update
    issue = github_issues.get_issue(repo_root, issue_number)

    # Update plan-header metadata with review_pr field
    try:
        updated_body = update_plan_header_review_pr(issue.body, pr_number)
    except Exception as e:
        raise CreateReviewPRException(
            error="metadata_update_failed",
            message=f"Failed to update plan metadata: {e}",
        ) from e

    # Write updated body back to issue
    try:
        github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
    except Exception as e:
        raise CreateReviewPRException(
            error="metadata_update_failed",
            message=f"Failed to write updated metadata to issue: {e}",
        ) from e

    # Construct PR URL
    pr_url = f"https://github.com/schrockn/erk/pull/{pr_number}"

    return CreateReviewPRSuccess(
        success=True,
        issue_number=issue_number,
        pr_number=pr_number,
        pr_url=pr_url,
    )


@click.command(name="plan-create-review-pr")
@click.argument("issue_number", type=int)
@click.argument("branch_name", type=str)
@click.argument("plan_title", type=str)
@click.pass_context
def plan_create_review_pr(
    ctx: click.Context,
    issue_number: int,
    branch_name: str,
    plan_title: str,
) -> None:
    """Create a draft PR for plan review and update plan metadata.

    Creates a draft PR from the specified branch targeting master, then updates
    the plan issue's metadata with the review_pr field.
    """
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    try:
        result = _create_review_pr_impl(
            github,
            github_issues=github.issues,
            repo_root=repo_root,
            issue_number=issue_number,
            branch_name=branch_name,
            plan_title=plan_title,
        )
        click.echo(json.dumps(asdict(result)))
    except CreateReviewPRException as e:
        error_response = CreateReviewPRError(
            success=False,
            error=e.error,
            message=e.message,
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1) from None
