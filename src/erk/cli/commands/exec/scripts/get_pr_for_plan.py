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
    require_github as require_github_gateway,
)
from erk_shared.context.helpers import require_repo_root
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
    github = require_github_gateway(ctx)
    repo_root = require_repo_root(ctx)
    # Draft-PR: plan_id IS the PR number — look up directly
    pr_result = github.get_pr(repo_root, issue_number)
    if isinstance(pr_result, PRNotFound):
        return _exit_with_error(
            error="no-pr-for-branch", message=f"PR #{issue_number} not found"
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
