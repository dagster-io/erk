"""Update step plan/PR cells in an objective's roadmap table.

Why this command exists (instead of using update-issue-body directly):

    The alternative is "fetch body → parse markdown table → find step row →
    surgically edit the Plan/PR cells → write entire body back". That's ~15
    lines of fragile ad-hoc Python that every caller (skills, hooks, scripts)
    must duplicate. The roadmap table has a specific structure
    (| step_id | description | status | plan | pr |) and the update has
    specific semantics:

    1. Find the row by step ID across all phases
    2. Compute display status from the plan/PR values
    3. Write status, plan, and PR cells atomically so the table is
       always human-readable without requiring a parse pass

    Encoding this once in a tested CLI command means:
    - No duplicated table-parsing logic across callers
    - Testable edge cases (step not found, no roadmap, clearing PR)
    - Atomic mental model: "update step 1.3's plan/PR to X"
    - Resilient to roadmap format changes (one command updates, not N sites)

Usage:
    # Single step — plan reference
    erk exec update-roadmap-step 6423 --step 1.3 --plan "#6464"

    # Single step — landed PR (auto-clears plan)
    erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"
    erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500" --status done

    # Clear both
    erk exec update-roadmap-step 6423 --step 1.3 --pr ""

    # Multiple steps
    erk exec update-roadmap-step 6697 --step 5.1 --step 5.2 --step 5.3 --plan "#6759"

Output:
    Single step: JSON with {success, issue_number, step_id,
        previous_plan, new_plan, previous_pr, new_pr, url}
    Multiple steps: JSON with {success, issue_number, new_plan, new_pr,
        url, steps: [...]}
        Each step result: {step_id, success, previous_plan, previous_pr, error}

Exit Codes:
    0: Always. Check JSON "success" field for pass/fail.
"""

import json
import re
from typing import get_args

import click

from erk.cli.commands.exec.scripts.objective_roadmap_shared import RoadmapStepStatus, parse_roadmap
from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_raw_metadata_blocks,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.types import BodyText


def _step_error_message(step_id: str, issue_number: int, error: object) -> str:
    if error == "step_not_found":
        return f"Step '{step_id}' not found in issue #{issue_number}"
    return f"Failed to replace cells for step '{step_id}'"


def _build_output(
    *,
    issue_number: int,
    step: tuple[str, ...],
    plan_value: str | None,
    pr_value: str | None,
    url: str,
    results: list[dict[str, object]],
    include_body: bool,
    updated_body: str | None,
) -> dict[str, object]:
    """Build JSON output dict, using legacy format for single step."""
    # Normalize empty strings to None for JSON output
    plan_out = plan_value if plan_value else None
    pr_out = pr_value if pr_value else None

    if len(step) != 1:
        output: dict[str, object] = {
            "success": all(r["success"] for r in results),
            "issue_number": issue_number,
            "new_plan": plan_out,
            "new_pr": pr_out,
            "url": url,
            "steps": results,
        }
        if include_body and all(r["success"] for r in results) and updated_body is not None:
            output["updated_body"] = updated_body
        return output
    single_result = results[0]
    if not single_result["success"]:
        return {
            "success": False,
            "error": single_result["error"],
            "message": _step_error_message(step[0], issue_number, single_result["error"]),
        }
    output = {
        "success": True,
        "issue_number": issue_number,
        "step_id": step[0],
        "previous_plan": single_result.get("previous_plan"),
        "new_plan": plan_out,
        "previous_pr": single_result.get("previous_pr"),
        "new_pr": pr_out,
        "url": url,
    }
    if include_body and updated_body is not None:
        output["updated_body"] = updated_body
    return output


def _find_step_refs(body: str, step_id: str) -> tuple[str | None, str | None, bool]:
    """Find the current plan and PR values for a step in the roadmap body.

    Returns:
        (previous_plan, previous_pr, found)
    """
    phases, _ = parse_roadmap(body)
    for phase in phases:
        for step in phase.steps:
            if step.id == step_id:
                return step.plan, step.pr, True
    return None, None, False


def _replace_step_refs_in_body(
    body: str,
    step_id: str,
    *,
    new_plan: str | None,
    new_pr: str | None,
    explicit_status: str | None,
) -> str | None:
    """Replace the plan/PR cells for a step in the raw markdown body.

    Checks for frontmatter first within objective-roadmap metadata block.
    Falls back to regex table replacement for backward compatibility.

    When frontmatter exists, updates both frontmatter (source of truth)
    and markdown table (rendered view) to keep them in sync.

    Args:
        body: Full issue body text.
        step_id: Step ID to update (e.g., "1.3").
        new_plan: New plan value. None=preserve existing, ""=clear, "#6464"=set.
        new_pr: New PR value. None=preserve existing, ""=clear, "#123"=set.
        explicit_status: If provided, use this status instead of inferring.

    Returns:
        Updated body string, or None if the step row was not found.
    """
    # Check for frontmatter-aware path
    raw_blocks = extract_raw_metadata_blocks(body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is not None:
        # Import here to avoid circular dependency
        from erk.cli.commands.exec.scripts.objective_roadmap_frontmatter import (
            update_step_in_frontmatter,
        )

        # Pass None through to frontmatter API (preserves existing value).
        # Non-None values (including "") are forwarded as-is.
        updated_block_content = update_step_in_frontmatter(
            roadmap_block.body,
            step_id,
            plan=new_plan,
            pr=new_pr,
            status=explicit_status,
        )

        if updated_block_content is None:
            return None

        new_block_with_markers = (
            f"<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
            f"<!-- erk:metadata-block:objective-roadmap -->\n"
            f"{updated_block_content}\n"
            f"<!-- /erk:metadata-block:objective-roadmap -->"
        )
        try:
            body = replace_metadata_block_in_body(
                body,
                "objective-roadmap",
                new_block_with_markers,
            )
        except ValueError:
            return None

    # Also update the markdown table (either as fallback or to keep in sync)
    # 5-col row: | step_id | description | status | plan | pr |
    pattern = re.compile(
        r"^\|(\s*" + re.escape(step_id) + r"\s*)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$",
        re.MULTILINE,
    )

    match = pattern.search(body)
    if match is None:
        # If we updated frontmatter but can't find table row, still return body
        if roadmap_block is not None:
            return body
        return None

    # Resolve None → preserve existing value from matched row
    existing_plan = match.group(4).strip()
    existing_pr = match.group(5).strip()

    resolved_plan = existing_plan if new_plan is None else (new_plan if new_plan else "-")
    resolved_pr = existing_pr if new_pr is None else (new_pr if new_pr else "-")

    # Determine display status
    if explicit_status is not None:
        display_status = explicit_status.replace("_", "-")
    elif resolved_pr != "-" and resolved_pr:
        display_status = "done"
    elif resolved_plan != "-" and resolved_plan:
        display_status = "in-progress"
    else:
        display_status = "pending"

    plan_display = resolved_plan
    pr_display = resolved_pr

    replacement = (
        f"|{match.group(1)}|{match.group(2)}| {display_status} | {plan_display} | {pr_display} |"
    )

    body = body[: match.start()] + replacement + body[match.end() :]

    return body


@click.command(name="update-roadmap-step")
@click.argument("issue_number", type=int)
@click.option("--step", required=True, multiple=True, help="Step ID(s) to update (e.g., '1.3')")
@click.option(
    "--plan",
    "plan_ref",
    help="Plan issue reference (e.g., '#6464')",
)
@click.option(
    "--pr",
    "pr_ref",
    help="PR reference (e.g., '#456', or '' to clear)",
)
@click.option(
    "--status",
    "explicit_status",
    required=False,
    default=None,
    type=click.Choice(list(get_args(RoadmapStepStatus))),
    help="Explicit status to set (default: infer from plan/PR value)",
)
@click.option(
    "--include-body",
    "include_body",
    is_flag=True,
    default=False,
    help="Include the fully-mutated issue body in JSON output as 'updated_body'",
)
@click.pass_context
def update_roadmap_step(
    ctx: click.Context,
    issue_number: int,
    *,
    step: tuple[str, ...],
    plan_ref: str | None,
    pr_ref: str | None,
    explicit_status: str | None,
    include_body: bool,
) -> None:
    """Update step plan/PR cells in an objective's roadmap table."""
    # Require at least one of --plan or --pr
    if plan_ref is None and pr_ref is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "missing_ref",
                    "message": "At least one of --plan or --pr is required",
                }
            )
        )
        raise SystemExit(0)

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
        raise SystemExit(0)

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
        raise SystemExit(0)

    # Validate all steps exist before processing any
    all_step_ids = {s.id for phase in phases for s in phase.steps}
    missing_steps = [s for s in step if s not in all_step_ids]
    if missing_steps:
        results = [
            {"step_id": s, "success": False, "error": "step_not_found"} for s in missing_steps
        ]
        output = _build_output(
            issue_number=issue_number,
            step=step,
            plan_value=plan_ref,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
        )
        click.echo(json.dumps(output))
        raise SystemExit(0)

    # Process multiple steps with single API call
    results: list[dict[str, object]] = []
    updated_body = issue.body
    any_failure = False

    for step_id in step:
        previous_plan, previous_pr, found = _find_step_refs(updated_body, step_id)
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

        new_body = _replace_step_refs_in_body(
            updated_body,
            step_id,
            new_plan=plan_ref,
            new_pr=pr_ref,
            explicit_status=explicit_status,
        )
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
                "previous_plan": previous_plan,
                "previous_pr": previous_pr,
            }
        )

    # Exit early if all steps failed
    if any_failure and not any(r["success"] for r in results):
        output = _build_output(
            issue_number=issue_number,
            step=step,
            plan_value=plan_ref,
            pr_value=pr_ref,
            url=issue.url,
            results=results,
            include_body=False,
            updated_body=None,
        )
        click.echo(json.dumps(output))
        raise SystemExit(0)

    # Single API call to write all updates
    github.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # Build and emit output
    output = _build_output(
        issue_number=issue_number,
        step=step,
        plan_value=plan_ref,
        pr_value=pr_ref,
        url=issue.url,
        results=results,
        include_body=include_body,
        updated_body=updated_body,
    )
    click.echo(json.dumps(output))
