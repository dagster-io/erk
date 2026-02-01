"""Fetch all context needed for objective-update-with-landed-pr in one call.

Bundles objective issue, plan issue, and PR details into a single JSON blob,
eliminating multiple sequential LLM turns for data fetching.

Usage:
    erk exec objective-update-context --pr 6517 --objective 6423 --branch P6513-...

Output:
    JSON with {success, objective, plan, pr} or {success, error}

Exit Codes:
    0: Success - all data fetched
    1: Error - missing data or invalid arguments
"""

import json
import re

import click

from erk_shared.context.helpers import require_github, require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import PRNotFound


def _parse_plan_number_from_branch(branch: str) -> int | None:
    """Extract plan issue number from branch pattern P<number>-..."""
    match = re.match(r"^P(\d+)-", branch)
    if match is None:
        return None
    return int(match.group(1))


def _error_json(error: str) -> str:
    return json.dumps({"success": False, "error": error})


@click.command(name="objective-update-context")
@click.option("--pr", "pr_number", type=int, required=True, help="PR number")
@click.option("--objective", "objective_number", type=int, required=True, help="Objective issue")
@click.option("--branch", "branch_name", type=str, required=True, help="Branch name")
@click.pass_context
def objective_update_context(
    ctx: click.Context,
    *,
    pr_number: int,
    objective_number: int,
    branch_name: str,
) -> None:
    """Fetch all context for objective update in a single call."""
    issues = require_issues(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    # Parse plan number from branch
    plan_number = _parse_plan_number_from_branch(branch_name)
    if plan_number is None:
        click.echo(_error_json(f"Branch '{branch_name}' does not match P<number>-... pattern"))
        raise SystemExit(1)

    # Fetch objective issue
    objective = issues.get_issue(repo_root, objective_number)
    if isinstance(objective, IssueNotFound):
        click.echo(_error_json(f"Objective issue #{objective_number} not found"))
        raise SystemExit(1)

    # Fetch plan issue
    plan = issues.get_issue(repo_root, plan_number)
    if isinstance(plan, IssueNotFound):
        click.echo(_error_json(f"Plan issue #{plan_number} not found"))
        raise SystemExit(1)

    # Fetch PR details
    pr = github.get_pr(repo_root, pr_number)
    if isinstance(pr, PRNotFound):
        click.echo(_error_json(f"PR #{pr_number} not found"))
        raise SystemExit(1)

    click.echo(
        json.dumps(
            {
                "success": True,
                "objective": {
                    "number": objective.number,
                    "title": objective.title,
                    "body": objective.body,
                    "state": objective.state,
                    "labels": objective.labels,
                    "url": objective.url,
                },
                "plan": {
                    "number": plan.number,
                    "title": plan.title,
                    "body": plan.body,
                },
                "pr": {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "url": pr.url,
                },
            }
        )
    )
