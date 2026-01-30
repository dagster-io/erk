"""Parse an objective's roadmap tables and return structured JSON.

Usage:
    erk exec objective-roadmap-check <OBJECTIVE_NUMBER>

Output:
    JSON with {success, issue_number, title, phases, summary, next_step, validation_errors}

Exit Codes:
    0: Success - roadmap parsed (even with validation warnings)
    1: Error - issue not found, API error, or critical validation failure
"""

import json

import click

from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    compute_summary,
    find_next_step,
    parse_roadmap,
    serialize_phases,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)
from erk_shared.gateway.github.issues.types import IssueNotFound


@click.command(name="objective-roadmap-check")
@click.argument("objective_number", type=int)
@click.pass_context
def objective_roadmap_check(ctx: click.Context, objective_number: int) -> None:
    """Parse an objective's roadmap tables and return structured JSON."""
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    issue = github.get_issue(repo_root, objective_number)
    if isinstance(issue, IssueNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Issue #{objective_number} not found",
                }
            )
        )
        raise SystemExit(1)

    # Parse the roadmap
    phases, validation_errors = parse_roadmap(issue.body)

    # If we have critical errors (no phases parsed), return failure
    has_phases = len(phases) > 0
    success = has_phases

    if not success:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "issue_number": issue.number,
                    "title": issue.title,
                    "validation_errors": validation_errors,
                }
            )
        )
        raise SystemExit(1)

    # Compute summary and next step
    summary = compute_summary(phases)
    next_step = find_next_step(phases)

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue.number,
                "title": issue.title,
                "phases": serialize_phases(phases),
                "summary": summary,
                "next_step": next_step,
                "validation_errors": validation_errors,
            }
        )
    )
