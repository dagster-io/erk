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
    require_branch_manager,
    require_git,
    require_github,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import PlanHeaderNotFoundError, PlanNotFound


@dataclass(frozen=True)
class PlanReviewCompleteSuccess:
    """Success response for plan review PR completion."""

    success: bool
    issue_number: int
    pr_number: int
    branch_name: str
    branch_deleted: bool
    local_branch_deleted: bool


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
    git: Git,
    branch_manager: BranchManager,
    backend: PlanBackend,
    repo_root: Path,
    issue_number: int,
) -> PlanReviewCompleteSuccess:
    """Close a plan review PR without merging.

    Args:
        github: GitHub gateway
        git: Git gateway (for query operations)
        branch_manager: BranchManager (for branch mutations)
        backend: PlanBackend for plan metadata operations
        repo_root: Repository root path
        issue_number: Plan issue number

    Returns:
        PlanReviewCompleteSuccess on success

    Raises:
        PlanReviewCompleteException: If issue not found, no plan header, or no review PR
    """
    plan_id = str(issue_number)

    # LBYL: Get review_pr from plan-header metadata (also serves as existence check)
    review_pr = backend.get_metadata_field(repo_root, plan_id, "review_pr")
    if isinstance(review_pr, PlanNotFound):
        raise PlanReviewCompleteException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    # LBYL: Check review_pr is not None
    if review_pr is None:
        raise PlanReviewCompleteException(
            error="no_review_pr",
            message=f"Issue #{issue_number} has no active review PR",
        )

    # review_pr should be an int at this point (from YAML metadata)
    if not isinstance(review_pr, int):
        raise PlanReviewCompleteException(
            error="no_review_pr",
            message=f"Issue #{issue_number} has invalid review_pr value",
        )
    review_pr_number = review_pr

    # Get PR details before closing (need branch name for deletion)
    pr_result = github.get_pr(repo_root, review_pr_number)
    if isinstance(pr_result, PRNotFound):
        raise PlanReviewCompleteException(
            error="pr_not_found",
            message=f"PR #{review_pr_number} not found",
        )
    branch_name = pr_result.head_ref_name

    # Close the PR
    github.close_pr(repo_root, review_pr_number)

    # Delete the review branch
    branch_deleted = github.delete_remote_branch(repo_root, branch_name)

    # LBYL: Switch to master if currently on the review branch
    current_branch = git.branch.get_current_branch(repo_root)
    if current_branch == branch_name:
        branch_manager.checkout_branch(repo_root, "master")

    # LBYL: Delete local branch if it exists
    local_branches = git.branch.list_local_branches(repo_root)
    local_branch_deleted = False
    if branch_name in local_branches:
        branch_manager.delete_branch(repo_root, branch_name, force=True)
        local_branch_deleted = True

    # Clear review_pr metadata (archives to last_review_pr)
    try:
        metadata = {"review_pr": None, "last_review_pr": review_pr_number}
        backend.update_metadata(repo_root, plan_id, metadata)
    except PlanHeaderNotFoundError:
        raise PlanReviewCompleteException(
            error="no_plan_header",
            message=f"Issue #{issue_number} is missing plan-header metadata block",
        ) from None

    return PlanReviewCompleteSuccess(
        success=True,
        issue_number=issue_number,
        pr_number=review_pr_number,
        branch_name=branch_name,
        branch_deleted=branch_deleted,
        local_branch_deleted=local_branch_deleted,
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
    git = require_git(ctx)
    branch_manager = require_branch_manager(ctx)
    github = require_github(ctx)
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    try:
        result = _plan_review_complete_impl(
            github,
            git=git,
            branch_manager=branch_manager,
            backend=backend,
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
