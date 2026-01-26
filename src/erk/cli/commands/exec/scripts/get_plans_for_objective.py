"""Fetch erk-plan issues linked to an objective.

Usage:
    erk exec get-plans-for-objective <OBJECTIVE_NUMBER>

Output:
    JSON with {success, objective_number, plans: [{number, state, title}]}

Exit Codes:
    0: Success - plans fetched
    1: Error - API error
"""

import json

import click

from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)
from erk_shared.gateway.github.metadata.core import find_metadata_block


@click.command(name="get-plans-for-objective")
@click.argument("objective_number", type=int)
@click.pass_context
def get_plans_for_objective(ctx: click.Context, objective_number: int) -> None:
    """Fetch erk-plan issues linked to an objective.

    Lists all issues with the erk-plan label, then filters to those
    whose plan-header metadata contains objective_id matching the
    given objective number.
    """
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    try:
        all_plans = github.list_issues(
            repo_root=repo_root,
            labels=["erk-plan"],
            state="all",
        )
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to list erk-plan issues: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Filter plans that reference this objective
    linked_plans = []
    for plan in all_plans:
        block = find_metadata_block(plan.body, "plan-header")
        if block is None:
            continue

        # Check both objective_id (new) and objective_issue (legacy)
        obj_id = block.data.get("objective_id") or block.data.get("objective_issue")
        if obj_id == objective_number:
            linked_plans.append(
                {
                    "number": plan.number,
                    "state": plan.state,
                    "title": plan.title,
                }
            )

    click.echo(
        json.dumps(
            {
                "success": True,
                "objective_number": objective_number,
                "plans": linked_plans,
            }
        )
    )
