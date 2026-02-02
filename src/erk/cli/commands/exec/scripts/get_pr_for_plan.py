"""Get PR details for a plan issue.

Usage:
    erk exec get-pr-for-plan <issue-number>

Extracts branch_name from plan metadata, then fetches PR for that branch.

Output:
    JSON with PR details or error if not found.
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import NoReturn

import click

from erk_shared.context.helpers import require_github as require_github_gateway
from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
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
    github_issues = require_github_issues(ctx)
    github = require_github_gateway(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue
    issue = github_issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        _exit_with_error(error="plan-not-found", message=f"Issue #{issue_number} not found")

    # Extract plan-header block
    block = find_metadata_block(issue.body, "plan-header")
    if block is None:
        _exit_with_error(
            error="no-branch-in-plan",
            message=f"Issue #{issue_number} has no plan-header metadata block",
        )

    # Get branch_name field
    branch_name = block.data.get("branch_name")
    if branch_name is None:
        # Attempt to infer branch from current git context
        # This handles cases where impl-signal failed to set branch_name
        git_branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )

        if git_branch_result.returncode == 0:
            current_branch = git_branch_result.stdout.strip()
            # Check if branch matches erk naming pattern: P{issue}-*
            if current_branch.startswith(f"P{issue_number}-"):
                branch_name = current_branch
            else:
                _exit_with_error(
                    error="no-branch-in-plan",
                    message=f"Issue #{issue_number} plan-header has no branch_name field",
                )
        else:
            _exit_with_error(
                error="no-branch-in-plan",
                message=f"Issue #{issue_number} plan-header has no branch_name field",
            )

    # Fetch PR for branch
    pr_result = github.get_pr_for_branch(repo_root, branch_name)
    if isinstance(pr_result, PRNotFound):
        _exit_with_error(
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
