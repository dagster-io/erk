"""Update a step's PR cell in an objective's roadmap table.

Why this command exists (instead of using update-issue-body directly):

    The alternative is "fetch body → parse markdown table → find step row →
    surgically edit the PR cell → write entire body back". That's ~15 lines
    of fragile ad-hoc Python that every caller (skills, hooks, scripts) must
    duplicate. The roadmap table has a specific structure
    (| step_id | description | status | pr |) and the update has specific
    semantics:

    1. Find the row by step ID across all phases
    2. Replace the PR cell with the new value
    3. Reset the status cell to "-" so parse_roadmap's inference logic
       determines the correct status from the PR column (e.g., "#123" → done,
       "plan #123" → in_progress, empty → pending)

    Encoding this once in a tested CLI command means:
    - No duplicated table-parsing logic across callers
    - Testable edge cases (step not found, no roadmap, clearing PR)
    - Atomic mental model: "update step 1.3's PR to X"
    - Resilient to roadmap format changes (one command updates, not N sites)

Usage:
    erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
    erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"
    erk exec update-roadmap-step 6423 --step 1.3 --pr ""

Output:
    JSON with {success, issue_number, step_id, previous_pr, new_pr, url}

Exit Codes:
    0: Success - step updated
    1: Error - issue/step not found, no roadmap, or API error
"""

import json
import re

import click

from erk.cli.commands.exec.scripts.objective_roadmap_shared import parse_roadmap
from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import BodyText


def _find_step_pr(body: str, step_id: str) -> tuple[str | None, bool]:
    """Find the current PR value for a step in the roadmap body.

    Returns:
        (previous_pr, found) where previous_pr is the current PR cell value
        (None if empty/"-") and found indicates whether the step was located.
    """
    phases, _ = parse_roadmap(body)
    for phase in phases:
        for step in phase.steps:
            if step.id == step_id:
                return step.pr, True
    return None, False


def _replace_step_pr_in_body(body: str, step_id: str, new_pr: str) -> str | None:
    """Replace the PR cell for a step in the raw markdown body.

    Uses regex to find the table row matching the step ID and replace
    the status and pr cells. Supports both 4-column and 7-column formats.

    For 7-column format, preserves Type, Issue, and Depends On cells.
    For 4-column format, only updates status and pr cells.

    Returns:
        Updated body string, or None if the step row was not found.
    """
    # Try 7-column format first: | step_id | description | type | issue | depends_on | status | pr |
    # We preserve the first 5 cells and replace the last 2 (status and pr)
    pattern_7col = re.compile(
        r"^\|(\s*" + re.escape(step_id) + r"\s*)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$",
        re.MULTILINE,
    )

    match_7col = pattern_7col.search(body)
    if match_7col is not None:
        # Determine display status from PR value
        if new_pr.startswith("#"):
            display_status = "done"
        elif new_pr.startswith("plan #"):
            display_status = "in-progress"
        else:
            display_status = "pending"

        # Build replacement: preserve step_id, description, type, issue, depends_on
        # and set computed status and pr
        pr_display = new_pr if new_pr else "-"
        replacement = (
            f"|{match_7col.group(1)}|{match_7col.group(2)}|{match_7col.group(3)}|"
            f"{match_7col.group(4)}|{match_7col.group(5)}| {display_status} | {pr_display} |"
        )

        return body[: match_7col.start()] + replacement + body[match_7col.end() :]

    # Fall back to 4-column format: | step_id | description | status | pr |
    # The step_id is in the first cell, and we need to replace status and pr cells.
    pattern_4col = re.compile(
        r"^\|(\s*" + re.escape(step_id) + r"\s*)\|(.+?)\|(.+?)\|(.+?)\|$",
        re.MULTILINE,
    )

    match_4col = pattern_4col.search(body)
    if match_4col is None:
        return None

    # Determine display status from PR value
    if new_pr.startswith("#"):
        display_status = "done"
    elif new_pr.startswith("plan #"):
        display_status = "in-progress"
    else:
        display_status = "pending"

    # Build replacement: preserve step_id cell and description cell,
    # set computed status and pr
    pr_display = new_pr if new_pr else "-"
    replacement = f"|{match_4col.group(1)}|{match_4col.group(2)}| {display_status} | {pr_display} |"

    return body[: match_4col.start()] + replacement + body[match_4col.end() :]


@click.command(name="update-roadmap-step")
@click.argument("issue_number", type=int)
@click.option("--step", required=True, help="Step ID to update (e.g., '1.3')")
@click.option(
    "--pr", required=True, help="PR reference (e.g., 'plan #123', '#456', or '' to clear)"
)
@click.pass_context
def update_roadmap_step(ctx: click.Context, issue_number: int, *, step: str, pr: str) -> None:
    """Update a step's PR cell in an objective's roadmap table."""
    github = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch the issue
    issue = github.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "issue_not_found",
                    "message": f"Issue #{issue_number} not found",
                }
            )
        )
        raise SystemExit(1)

    # Parse roadmap to validate it exists
    phases, _ = parse_roadmap(issue.body)
    if not phases:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_roadmap",
                    "message": f"Issue #{issue_number} has no roadmap table",
                }
            )
        )
        raise SystemExit(1)

    # Find the step's current PR value
    previous_pr, found = _find_step_pr(issue.body, step)
    if not found:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "step_not_found",
                    "message": f"Step '{step}' not found in issue #{issue_number}",
                }
            )
        )
        raise SystemExit(1)

    # Replace the PR cell in the raw body
    updated_body = _replace_step_pr_in_body(issue.body, step, pr)
    if updated_body is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "replacement_failed",
                    "message": f"Failed to replace PR cell for step '{step}'",
                }
            )
        )
        raise SystemExit(1)

    # Write the updated body back
    github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "step_id": step,
                "previous_pr": previous_pr,
                "new_pr": pr if pr else None,
                "url": issue.url,
            }
        )
    )
