"""Update step PR cells in an objective's roadmap table.

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
    # Single step
    erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
    erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"
    erk exec update-roadmap-step 6423 --step 1.3 --pr ""

    # Multiple steps
    erk exec update-roadmap-step 6697 --step 5.1 --step 5.2 --step 5.3 --pr "plan #6759"

Output:
    Single step: JSON with {success, issue_number, step_id, previous_pr, new_pr, url}
    Multiple steps: JSON with {success, issue_number, new_pr, url, steps: [...]}
        Each step result: {step_id, success, previous_pr, error}

Exit Codes:
    0: Success (all steps updated) or multi-step with errors (check JSON success field)
    1: Error - issue/roadmap not found, API error (single-step mode)
"""

import json
import re

import click

from erk.cli.commands.exec.scripts.objective_roadmap_shared import parse_roadmap
from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import BodyText


def _step_error_message(step_id: str, issue_number: int, error: object) -> str:
    if error == "step_not_found":
        return f"Step '{step_id}' not found in issue #{issue_number}"
    return f"Failed to replace PR cell for step '{step_id}'"


def _build_output(
    *,
    issue_number: int,
    step: tuple[str, ...],
    pr: str,
    url: str,
    results: list[dict[str, object]],
    all_failed: bool,
) -> dict[str, object]:
    """Build JSON output dict, using legacy format for single step."""
    if len(step) == 1:
        single_result = results[0]
        if not single_result["success"]:
            return {
                "success": False,
                "error": single_result["error"],
                "message": _step_error_message(step[0], issue_number, single_result["error"]),
            }
        return {
            "success": True,
            "issue_number": issue_number,
            "step_id": step[0],
            "previous_pr": single_result.get("previous_pr"),
            "new_pr": pr or None,
            "url": url,
        }
    return {
        "success": not all_failed,
        "issue_number": issue_number,
        "new_pr": pr or None,
        "url": url,
        "steps": results,
    }


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
    the last two cells (status and pr). The status is computed from the PR
    value to provide human-readable status in the roadmap table.

    Returns:
        Updated body string, or None if the step row was not found.
    """
    # Match table row: | step_id | description | status | pr |
    # The step_id is in the first cell, and we need to replace status and pr cells.
    pattern = re.compile(
        r"^\|(\s*" + re.escape(step_id) + r"\s*)\|(.+?)\|(.+?)\|(.+?)\|$",
        re.MULTILINE,
    )

    match = pattern.search(body)
    if match is None:
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
    replacement = f"|{match.group(1)}|{match.group(2)}| {display_status} | {pr_display} |"

    return body[: match.start()] + replacement + body[match.end() :]


@click.command(name="update-roadmap-step")
@click.argument("issue_number", type=int)
@click.option("--step", required=True, multiple=True, help="Step ID(s) to update (e.g., '1.3')")
@click.option(
    "--pr", required=True, help="PR reference (e.g., 'plan #123', '#456', or '' to clear)"
)
@click.pass_context
def update_roadmap_step(
    ctx: click.Context, issue_number: int, *, step: tuple[str, ...], pr: str
) -> None:
    """Update step PR cells in an objective's roadmap table."""
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

    # Validate all steps exist before processing any
    all_step_ids = {s.id for phase in phases for s in phase.steps}
    missing_steps = [s for s in step if s not in all_step_ids]
    if missing_steps:
        results = [
            {"step_id": s, "success": False, "error": "step_not_found"}
            for s in missing_steps
        ]
        output = _build_output(
            issue_number=issue_number,
            step=step,
            pr=pr,
            url=issue.url,
            results=results,
            all_failed=True,
        )
        click.echo(json.dumps(output))
        raise SystemExit(1 if len(step) == 1 else 0)

    # Process multiple steps with single API call
    results: list[dict[str, object]] = []
    updated_body = issue.body
    any_failure = False

    for step_id in step:
        previous_pr, found = _find_step_pr(updated_body, step_id)
        if not found:
            results.append(
                {
                    "step_id": step_id,
                    "success": False,
                    "error": "step_not_found",
                }
            )
            any_failure = True
            continue

        new_body = _replace_step_pr_in_body(updated_body, step_id, pr)
        if new_body is None:
            results.append(
                {
                    "step_id": step_id,
                    "success": False,
                    "error": "replacement_failed",
                }
            )
            any_failure = True
            continue

        updated_body = new_body
        results.append(
            {
                "step_id": step_id,
                "success": True,
                "previous_pr": previous_pr,
            }
        )

    # Exit early if all steps failed
    if any_failure and not any(r["success"] for r in results):
        output = _build_output(
            issue_number=issue_number,
            step=step,
            pr=pr,
            url=issue.url,
            results=results,
            all_failed=True,
        )
        click.echo(json.dumps(output))
        raise SystemExit(1 if len(step) == 1 else 0)

    # Single API call to write all updates
    github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # Build and emit output
    output = _build_output(
        issue_number=issue_number,
        step=step,
        pr=pr,
        url=issue.url,
        results=results,
        all_failed=False,
    )
    click.echo(json.dumps(output))
    if any_failure:
        raise SystemExit(1 if len(step) == 1 else 0)
