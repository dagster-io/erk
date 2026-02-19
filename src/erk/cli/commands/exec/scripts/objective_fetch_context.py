"""Fetch all context needed for objective-update-with-landed-pr in one call.

Bundles objective issue, plan issue, PR details, and parsed roadmap context
into a single JSON blob, eliminating multiple sequential LLM turns for data
fetching and step matching.

Usage:
    erk exec objective-fetch-context --pr 6517 --objective 6423 --branch P6513-...
    erk exec objective-fetch-context  # auto-discovers all arguments

Output:
    JSON with {success, objective, plan, pr, roadmap} or {success, error}

Exit Codes:
    0: Success - all data fetched
    1: Error - missing data or invalid arguments
"""

import json

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import extract_raw_metadata_blocks
from erk_shared.gateway.github.metadata.dependency_graph import (
    build_graph,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.roadmap import (
    group_nodes_by_phase,
    parse_roadmap_frontmatter,
    serialize_phases,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.objective_fetch_context_result import (
    ObjectiveFetchContextErrorDict,
    ObjectiveFetchContextResultDict,
    ObjectiveInfoDict,
    PlanInfoDict,
    PRInfoDict,
    RoadmapContextDict,
)
from erk_shared.plan_store.types import PlanNotFound


def _error_json(error: str) -> str:
    result: ObjectiveFetchContextErrorDict = {"success": False, "error": error}
    return json.dumps(result)


def _build_roadmap_context(objective_body: str, plan_id: str) -> RoadmapContextDict:
    """Parse roadmap from objective body and match steps for this plan.

    Uses parse_roadmap_frontmatter() + group_nodes_by_phase() directly
    (not parse_roadmap() which enriches phase names from markdown headers).
    """
    raw_blocks = extract_raw_metadata_blocks(objective_body)
    matching_blocks = [block for block in raw_blocks if block.key == "objective-roadmap"]

    if not matching_blocks:
        return RoadmapContextDict(
            phases=[],
            matched_steps=[],
            summary={},
            next_node=None,
            all_complete=False,
        )

    steps = parse_roadmap_frontmatter(matching_blocks[0].body)
    if steps is None:
        return RoadmapContextDict(
            phases=[],
            matched_steps=[],
            summary={},
            next_node=None,
            all_complete=False,
        )

    phases = group_nodes_by_phase(steps)
    graph = build_graph(phases)

    plan_ref = f"#{plan_id}"
    matched_steps = [step.id for step in steps if step.plan == plan_ref]

    summary = compute_graph_summary(graph)
    next_node = find_graph_next_node(graph, phases)

    return RoadmapContextDict(
        phases=serialize_phases(phases),
        matched_steps=matched_steps,
        summary=summary,
        next_node=next_node,
        all_complete=graph.is_complete(),
    )


@click.command(name="objective-fetch-context")
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
@click.pass_context
def objective_fetch_context(
    ctx: click.Context,
    *,
    pr_number: int | None,
    objective_number: int | None,
    branch_name: str | None,
) -> None:
    """Fetch all context for objective update in a single call."""
    issues = require_issues(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)
    plan_backend = require_plan_backend(ctx)

    # Discovery: auto-fill branch from git state
    if branch_name is None:
        git = require_git(ctx)
        cwd = require_cwd(ctx)
        branch_name = git.branch.get_current_branch(cwd)
        if branch_name is None:
            click.echo(_error_json("Could not determine current branch (detached HEAD?)"))
            raise SystemExit(1)

    # Resolve plan from branch via backend (works for both P<number>- and plan-... branches)
    plan_result = plan_backend.get_plan_for_branch(repo_root, branch_name)
    if isinstance(plan_result, PlanNotFound):
        click.echo(_error_json(f"No plan found for branch '{branch_name}'"))
        raise SystemExit(1)

    plan_id = plan_result.plan_identifier

    # Discovery: auto-fill objective from plan metadata
    if objective_number is None:
        if plan_result.objective_id is None:
            msg = f"Plan #{plan_id} has no objective_issue in plan-header metadata"
            click.echo(_error_json(msg))
            raise SystemExit(1)
        objective_number = plan_result.objective_id

    # Discovery: auto-fill PR from branch
    if pr_number is None:
        pr_result = github.get_pr_for_branch(repo_root, branch_name)
        if isinstance(pr_result, PRNotFound):
            click.echo(_error_json(f"No PR found for branch '{branch_name}'"))
            raise SystemExit(1)
        pr_number = pr_result.number

    # Fetch objective issue
    objective = issues.get_issue(repo_root, objective_number)
    if isinstance(objective, IssueNotFound):
        click.echo(_error_json(f"Objective issue #{objective_number} not found"))
        raise SystemExit(1)

    # Fetch PR details
    pr = github.get_pr(repo_root, pr_number)
    if isinstance(pr, PRNotFound):
        click.echo(_error_json(f"PR #{pr_number} not found"))
        raise SystemExit(1)

    roadmap = _build_roadmap_context(objective.body, plan_id)

    objective_info: ObjectiveInfoDict = {
        "number": objective.number,
        "title": objective.title,
        "body": objective.body,
        "state": objective.state,
        "labels": objective.labels,
        "url": objective.url,
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
    result: ObjectiveFetchContextResultDict = {
        "success": True,
        "objective": objective_info,
        "plan": plan_info,
        "pr": pr_info,
        "roadmap": roadmap,
    }
    click.echo(json.dumps(result))
