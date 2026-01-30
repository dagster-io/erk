"""Update a step in an objective's roadmap table.

Usage:
    erk exec objective-roadmap-update <NUMBER> --step <ID>
        [--status <STATUS>] [--pr <PR_REF>]

At least one of --status or --pr must be provided.

Output:
    JSON with {success, issue_number, step, summary, validation_errors}

Exit Codes:
    0: Success - step updated and re-validated
    1: Error - step not found, issue not found, or validation failure
"""

import json
import re

import click

from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    RoadmapPhase,
    compute_summary,
    parse_roadmap,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)
from erk_shared.gateway.github.types import BodyText


def _find_step_row(body: str, step_id: str) -> re.Match[str] | None:
    """Find the table row matching a step ID.

    Looks for a markdown table row where the first cell matches the step_id exactly.

    Returns:
        The regex Match for the full row, or None if not found.
    """
    escaped_id = re.escape(step_id)
    pattern = re.compile(
        r"^\|\s*" + escaped_id + r"\s*\|(.+?)\|(.+?)\|(.+?)\|$",
        re.MULTILINE,
    )
    return pattern.search(body)


def _replace_row_cells(
    row_match: re.Match[str],
    step_id: str,
    *,
    status: str | None,
    pr: str | None,
) -> str:
    """Build a replacement row with updated cells.

    Only replaces cells for which a new value was provided.
    Preserves the original value for cells not being updated.
    """
    description = row_match.group(1).strip()
    original_status = row_match.group(2).strip()
    original_pr = row_match.group(3).strip()

    new_status = status if status is not None else original_status
    new_pr = pr if pr is not None else original_pr

    return f"| {step_id} | {description} | {new_status} | {new_pr} |"


def _update_step_in_body(
    body: str,
    step_id: str,
    *,
    status: str | None,
    pr: str | None,
) -> str | None:
    """Find and replace a step row in the body.

    Returns:
        The updated body string, or None if the step was not found.
    """
    row_match = _find_step_row(body, step_id)
    if row_match is None:
        return None

    new_row = _replace_row_cells(row_match, step_id, status=status, pr=pr)
    return body[: row_match.start()] + new_row + body[row_match.end() :]


def _find_step_in_phases(phases: list[RoadmapPhase], step_id: str) -> dict[str, str | None] | None:
    """Find a step by ID across all phases and return its data as a dict."""
    for phase in phases:
        for s in phase.steps:
            if s.id == step_id:
                return {
                    "id": s.id,
                    "description": s.description,
                    "status": s.status,
                    "pr": s.pr,
                }
    return None


@click.command(name="objective-roadmap-update")
@click.argument("objective_number", type=int)
@click.option("--step", required=True, help="Step ID to update (e.g. '2.1')")
@click.option(
    "--status",
    "new_status",
    default=None,
    help="New status value (e.g. 'done', 'blocked', 'skipped')",
)
@click.option("--pr", "new_pr", default=None, help="New PR reference (e.g. '#123', 'plan #456')")
@click.pass_context
def objective_roadmap_update(
    ctx: click.Context,
    objective_number: int,
    step: str,
    new_status: str | None,
    new_pr: str | None,
) -> None:
    """Update a step in an objective's roadmap table."""
    # Validate that at least one update flag is provided
    if new_status is None and new_pr is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "At least one of --status or --pr must be provided",
                }
            )
        )
        raise SystemExit(1)

    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch the issue
    try:
        issue = github.get_issue(repo_root, objective_number)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get issue #{objective_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Validate current body parses correctly
    phases, validation_errors = parse_roadmap(issue.body)
    if not phases:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Issue #{objective_number} has no valid roadmap phases",
                    "validation_errors": validation_errors,
                }
            )
        )
        raise SystemExit(1)

    # Perform the row-level update
    updated_body = _update_step_in_body(issue.body, step, status=new_status, pr=new_pr)
    if updated_body is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Step '{step}' not found in objective #{objective_number}",
                }
            )
        )
        raise SystemExit(1)

    # Write back the updated body
    github.update_issue_body(repo_root, objective_number, BodyText(content=updated_body))

    # Re-parse the updated body to validate and compute summary
    updated_phases, updated_validation_errors = parse_roadmap(updated_body)
    updated_summary = compute_summary(updated_phases)

    # Find the updated step in the re-parsed data
    updated_step_data = _find_step_in_phases(updated_phases, step)

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": objective_number,
                "step": updated_step_data,
                "summary": updated_summary,
                "validation_errors": updated_validation_errors,
            }
        )
    )
