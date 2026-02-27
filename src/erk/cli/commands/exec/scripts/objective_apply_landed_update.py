"""Apply mechanical updates to an objective after landing a PR.

Combines the fetch-context, update-nodes, and post-action-comment steps into
a single call, eliminating 5+ sequential agent commands.  Only prose
reconciliation (which requires LLM judgment) is left to the calling skill.

Usage:
    erk exec objective-apply-landed-update --pr 6517 --objective 6423 --branch P6513-...
    erk exec objective-apply-landed-update  # auto-discovers all arguments

Output:
    JSON with {success, objective, plan, pr, roadmap, node_updates,
    action_comment_id} or {success, error}

Exit Codes:
    0: Success - all mechanical updates applied
    1: Error - missing data or API failure
"""

import json
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.objective_fetch_context import (
    _build_roadmap_context,
    _fetch_objective_content,
)
from erk.cli.commands.exec.scripts.objective_post_action_comment import (
    _format_action_comment,
)
from erk.cli.commands.exec.scripts.update_objective_node import (
    _find_node_refs,
    _replace_node_refs_in_body,
)
from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_metadata_value,
)
from erk_shared.gateway.github.metadata.roadmap import rerender_comment_roadmap
from erk_shared.gateway.github.types import BodyText, PRNotFound
from erk_shared.objective_apply_landed_update_result import (
    ApplyLandedUpdateErrorDict,
    ApplyLandedUpdateResultDict,
    NodeUpdateDict,
)
from erk_shared.objective_fetch_context_result import (
    ObjectiveInfoDict,
    PlanInfoDict,
    PRInfoDict,
)
from erk_shared.plan_store.types import PlanNotFound


def _error_json(error: str) -> str:
    result: ApplyLandedUpdateErrorDict = {"success": False, "error": error}
    return json.dumps(result)


def _update_nodes_in_body(
    body: str,
    matched_steps: list[str],
    *,
    pr_ref: str,
) -> tuple[str, list[NodeUpdateDict]]:
    """Update all matched nodes to done with PR reference.

    Returns the updated body and a list of node update records.
    """
    node_updates: list[NodeUpdateDict] = []
    updated_body = body

    for node_id in matched_steps:
        previous_pr, found = _find_node_refs(updated_body, node_id)
        if not found:
            continue

        new_body = _replace_node_refs_in_body(
            updated_body,
            node_id,
            new_pr=pr_ref,
            explicit_status="done",
        )
        if new_body is None:
            continue

        updated_body = new_body
        node_updates.append(
            NodeUpdateDict(
                node_id=node_id,
                previous_pr=previous_pr,
            )
        )

    return updated_body, node_updates


def _update_comment_table(
    issues: GitHubIssues,
    repo_root: Path,
    updated_body: str,
) -> None:
    """Re-render the markdown table in the objective-body comment from YAML (v2 format)."""
    objective_comment_id = extract_metadata_value(
        updated_body, "objective-header", "objective_comment_id"
    )
    if objective_comment_id is None:
        return

    comment_body = issues.get_comment_by_id(repo_root, objective_comment_id)
    updated_comment = rerender_comment_roadmap(updated_body, comment_body)

    if updated_comment is not None and updated_comment != comment_body:
        issues.update_comment(repo_root, objective_comment_id, updated_comment)


@click.command(name="objective-apply-landed-update")
@click.option(
    "--pr", "pr_number", type=int, default=None, help="PR number (auto-discovered if omitted)"
)
@click.option(
    "--objective",
    "objective_number",
    type=int,
    default=None,
    help="Objective issue (auto-discovered if omitted)",
)
@click.option(
    "--branch",
    "branch_name",
    type=str,
    default=None,
    help="Branch name (auto-discovered if omitted)",
)
@click.option(
    "--plan",
    "plan_number",
    type=int,
    default=None,
    help="Plan number (direct lookup, skips branch-based discovery)",
)
@click.option(
    "--node",
    "node_ids",
    multiple=True,
    help="Node ID(s) to mark as done (e.g., --node 1.1 --node 1.2)",
)
@click.pass_context
def objective_apply_landed_update(
    ctx: click.Context,
    *,
    pr_number: int | None,
    objective_number: int | None,
    branch_name: str | None,
    plan_number: int | None,
    node_ids: tuple[str, ...],
) -> None:
    """Apply mechanical updates to an objective after landing a PR.

    Fetches context, updates roadmap nodes to done, and posts an action comment
    in a single call. Returns rich JSON for the agent to use in prose reconciliation.
    """
    issues = require_issues(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)
    plan_backend = require_plan_backend(ctx)
    time = require_time(ctx)

    # --- Discovery: auto-fill branch from git state ---
    if branch_name is None:
        git = require_git(ctx)
        cwd = require_cwd(ctx)
        branch_name = git.branch.get_current_branch(cwd)
        if branch_name is None:
            click.echo(_error_json("Could not determine current branch (detached HEAD?)"))
            raise SystemExit(1)

    # --- Resolve plan (direct lookup or branch-based discovery) ---
    if plan_number is not None:
        plan_result = plan_backend.get_plan(repo_root, str(plan_number))
        if isinstance(plan_result, PlanNotFound):
            click.echo(_error_json(f"Plan #{plan_number} not found"))
            raise SystemExit(1)
    else:
        plan_result = plan_backend.get_plan_for_branch(repo_root, branch_name)
        if isinstance(plan_result, PlanNotFound):
            click.echo(_error_json(f"No plan found for branch '{branch_name}'"))
            raise SystemExit(1)

    plan_id = plan_result.plan_identifier

    # --- Discovery: auto-fill objective from plan metadata ---
    if objective_number is None:
        if plan_result.objective_id is None:
            msg = f"Plan #{plan_id} has no objective_issue in plan-header metadata"
            click.echo(_error_json(msg))
            raise SystemExit(1)
        objective_number = plan_result.objective_id

    # --- Discovery: auto-fill PR from branch ---
    if pr_number is None:
        pr_result = github.get_pr_for_branch(repo_root, branch_name)
        if isinstance(pr_result, PRNotFound):
            click.echo(_error_json(f"No PR found for branch '{branch_name}'"))
            raise SystemExit(1)
        pr_number = pr_result.number

    # --- Fetch objective issue ---
    objective = issues.get_issue(repo_root, objective_number)
    if isinstance(objective, IssueNotFound):
        click.echo(_error_json(f"Objective #{objective_number} not found"))
        raise SystemExit(1)

    # --- Fetch PR details ---
    pr = github.get_pr(repo_root, pr_number)
    if isinstance(pr, PRNotFound):
        click.echo(_error_json(f"PR #{pr_number} not found"))
        raise SystemExit(1)

    # --- Build roadmap context ---
    roadmap = _build_roadmap_context(objective.body, plan_id)
    pr_ref = f"#{pr_number}"

    if node_ids:
        matched_steps = list(node_ids)
    else:
        matched_steps = [
            node["id"]
            for phase in roadmap["phases"]
            for node in phase["nodes"]
            if node["pr"] == pr_ref
        ]

    # --- Fetch objective prose content ---
    objective_content = _fetch_objective_content(objective.body, issues, repo_root)

    node_updates: list[NodeUpdateDict] = []
    if matched_steps:
        updated_body, node_updates = _update_nodes_in_body(
            objective.body,
            matched_steps,
            pr_ref=pr_ref,
        )

        # Write updated body to GitHub (single API call)
        issues.update_issue_body(repo_root, objective_number, BodyText(content=updated_body))

        # Re-render v2 comment table from updated YAML
        _update_comment_table(issues, repo_root, updated_body)

        # Rebuild roadmap from the updated body
        roadmap = _build_roadmap_context(updated_body, plan_id)

    # --- Post action comment ---
    date_str = time.now().strftime("%Y-%m-%d")
    phase_step = ", ".join(matched_steps) if matched_steps else "N/A"

    roadmap_updates = [f"Node {nid}: -> done" for nid in matched_steps]

    comment_body = _format_action_comment(
        title=f"Landed PR #{pr_number}",
        date=date_str,
        pr_number=pr_number,
        phase_step=phase_step,
        what_was_done=[f"Landed {pr.title} (#{pr_number})"],
        lessons_learned=[],
        roadmap_updates=roadmap_updates,
        body_reconciliation=[],
    )

    action_comment_id = issues.add_comment(repo_root, objective_number, comment_body)

    # --- Emit result ---
    objective_info: ObjectiveInfoDict = {
        "number": objective.number,
        "title": objective.title,
        "body": objective.body,
        "state": objective.state,
        "labels": objective.labels,
        "url": objective.url,
        "objective_content": objective_content,
    }
    plan_info: PlanInfoDict = {
        "number": plan_id,
        "title": plan_result.title,
        "body": plan_result.body,
    }
    pr_info: PRInfoDict = {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body,
        "url": pr.url,
    }
    result: ApplyLandedUpdateResultDict = {
        "success": True,
        "objective": objective_info,
        "plan": plan_info,
        "pr": pr_info,
        "roadmap": roadmap,
        "node_updates": node_updates,
        "action_comment_id": action_comment_id,
    }
    click.echo(json.dumps(result))
