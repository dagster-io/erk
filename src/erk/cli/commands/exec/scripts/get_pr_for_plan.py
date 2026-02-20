"""Get PR details for a plan issue.

Usage:
    erk exec get-pr-for-plan <issue-number>

Extracts branch_name from plan metadata, then fetches PR for that branch.

Output:
    JSON with PR details or error if not found.
"""

import json
from dataclasses import asdict, dataclass
from typing import NoReturn

import click

from erk_shared.context.helpers import (
    require_git,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_github as require_github_gateway,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.types import PRNotFound


@dataclass(frozen=True)
class GetPrForPlanSuccess:
    """Success response with PR details."""

    success: bool
    pr: dict[str, object]


@dataclass(frozen=True)
class GetPrForPlanError:
    """Error response for PR lookup."""

    success: bool
    error: str
    message: str


def _exit_with_error(*, error: str, message: str) -> NoReturn:
    """Output error JSON to stderr and exit with code 1."""
    result = GetPrForPlanError(success=False, error=error, message=message)
    click.echo(json.dumps(asdict(result)), err=True)
    raise SystemExit(1)


@click.command(name="get-pr-for-plan")
@click.argument("issue_number", type=int)
@click.pass_context
def get_pr_for_plan(
    ctx: click.Context,
    issue_number: int,
) -> None:
    """Get PR details for a plan issue.

    Fetches the issue, extracts the branch_name from plan-header metadata,
    and returns PR details for that branch.
    """
    plan_backend = require_plan_backend(ctx)
    github = require_github_gateway(ctx)
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)

    # Draft-PR shortcut: plan_id IS the PR number — look up directly
    if plan_backend.get_provider_name() == "github-draft-pr":
        pr_result = github.get_pr(repo_root, issue_number)
        if isinstance(pr_result, PRNotFound):
            return _exit_with_error(
                error="no-pr-for-branch",
                message=f"No draft PR found for plan #{issue_number}",
            )
        pr_data = {
            "number": pr_result.number,
            "title": pr_result.title,
            "state": pr_result.state,
            "url": pr_result.url,
            "head_ref_name": pr_result.head_ref_name,
            "base_ref_name": pr_result.base_ref_name,
        }
        success_result = GetPrForPlanSuccess(success=True, pr=pr_data)
        click.echo(json.dumps(asdict(success_result)))
        return

    github_issues = require_github_issues(ctx)

    # Fetch current issue
    issue = github_issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return _exit_with_error(error="plan-not-found", message=f"Issue #{issue_number} not found")

    # Extract plan-header block
    block = find_metadata_block(issue.body, "plan-header")
    if block is None:
        return _exit_with_error(
            error="no-branch-in-plan",
            message=f"Issue #{issue_number} has no plan-header metadata block",
        )

    # Get branch_name field
    branch_name: str | None = block.data.get("branch_name")
    if branch_name is None:
        # Attempt to infer branch from current git context
        # This handles cases where impl-signal failed to set branch_name
        current_branch = git.branch.get_current_branch(repo_root)
        if current_branch is not None and current_branch.startswith(f"P{issue_number}-"):
            branch_name = current_branch
        else:
            return _exit_with_error(
                error="no-branch-in-plan",
                message=f"Issue #{issue_number} plan-header has no branch_name field",
            )

    # At this point branch_name is guaranteed to be a string
    assert branch_name is not None

    # Fetch PR for branch (branch_name is guaranteed to be str here)
    pr_result = github.get_pr_for_branch(repo_root, branch_name)
    if isinstance(pr_result, PRNotFound):
        return _exit_with_error(
            error="no-pr-for-branch",
            message=f"No PR found for branch '{branch_name}'",
        )

    # Return PR details
    pr_data = {
        "number": pr_result.number,
        "title": pr_result.title,
        "state": pr_result.state,
        "url": pr_result.url,
        "head_ref_name": pr_result.head_ref_name,
        "base_ref_name": pr_result.base_ref_name,
    }
    success_result = GetPrForPlanSuccess(success=True, pr=pr_data)
    click.echo(json.dumps(asdict(success_result)))
