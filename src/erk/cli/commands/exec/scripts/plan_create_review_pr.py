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

from erk.cli.constants import ERK_PLAN_REVIEW_TITLE_PREFIX, ERK_PLAN_TITLE_PREFIX, PLAN_REVIEW_LABEL
from erk_shared.context.helpers import (
    get_repo_identifier,
    require_github,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import PlanHeaderNotFoundError, PlanNotFound


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

## Quick Start

Prepare worktree only:
```
erk prepare {issue_number}
```

Prepare and implement:
```
source "$(erk prepare {issue_number} --script)" && erk implement --dangerous
```

## Important

**This PR will not be merged.** It exists solely to enable inline review comments on the plan.

Once review is complete, the plan will be implemented directly and this PR will be closed.
"""


def _create_review_pr_impl(
    github: GitHub,
    *,
    backend: PlanBackend,
    repo_root: Path,
    repo_identifier: str,
    issue_number: int,
    branch_name: str,
    plan_title: str,
) -> CreateReviewPRSuccess:
    """Create a draft PR for plan review and update plan metadata.

    Args:
        github: GitHub gateway
        backend: PlanBackend for plan metadata operations
        repo_root: Repository root path
        repo_identifier: Repository identifier in "owner/repo" format
        issue_number: Plan issue number
        branch_name: Branch name for the PR
        plan_title: Title of the plan

    Returns:
        CreateReviewPRSuccess on success

    Raises:
        CreateReviewPRException: If issue not found or PR creation fails
    """
    plan_id = str(issue_number)

    # LBYL: Check if plan exists before proceeding (get_metadata_field is lightweight)
    if isinstance(backend.get_metadata_field(repo_root, plan_id, "schema_version"), PlanNotFound):
        raise CreateReviewPRException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    # LBYL: Check if a PR already exists for this branch
    existing_pr = github.get_pr_for_branch(repo_root, branch_name)
    if not isinstance(existing_pr, PRNotFound):
        raise CreateReviewPRException(
            error="pr_already_exists",
            message=f"PR #{existing_pr.number} already exists for branch {branch_name}",
        )

    # Create draft PR - strip [erk-plan] prefix if present, use [erk-plan-review] prefix
    pr_title = (
        f"{ERK_PLAN_REVIEW_TITLE_PREFIX}"
        f"{plan_title.removeprefix(ERK_PLAN_TITLE_PREFIX)} (#{issue_number})"
    )
    pr_body = _format_pr_body(issue_number, plan_title)

    pr_number = github.create_pr(
        repo_root,
        branch_name,
        pr_title,
        pr_body,
        base="master",
        draft=True,
    )

    # Add plan-review label to the PR
    github.add_label_to_pr(repo_root, pr_number, PLAN_REVIEW_LABEL)

    # Update plan-header metadata with review_pr field
    # PlanHeaderNotFoundError raised if plan has no plan-header block
    try:
        backend.update_metadata(repo_root, plan_id, {"review_pr": pr_number})
    except PlanHeaderNotFoundError:
        raise CreateReviewPRException(
            error="invalid_issue",
            message=f"Issue #{issue_number} is missing plan-header metadata block",
        ) from None

    # Construct PR URL
    pr_url = f"https://github.com/{repo_identifier}/pull/{pr_number}"

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
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    repo_identifier = get_repo_identifier(ctx)
    if repo_identifier is None:
        error_response = CreateReviewPRError(
            success=False,
            error="repo_not_found",
            message="Could not determine repository identifier",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    try:
        result = _create_review_pr_impl(
            github,
            backend=backend,
            repo_root=repo_root,
            repo_identifier=repo_identifier,
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
