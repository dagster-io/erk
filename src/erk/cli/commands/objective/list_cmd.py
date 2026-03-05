"""List open objectives."""

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk_shared.gateway.github.metadata.core import extract_objective_slug
from erk_shared.gateway.github.metadata.dependency_graph import (
    _TERMINAL_STATUSES,
    build_graph,
    build_state_sparkline,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.roadmap import parse_roadmap
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan


def _compute_slug(plan: Plan) -> str:
    if plan.body:
        slug = extract_objective_slug(plan.body)
        if slug is not None:
            return slug[:25]
    if plan.title:
        return plan.title.removeprefix("Objective: ")[:25]
    return "-"


def _compute_enriched_fields(plan: Plan) -> dict[str, str]:
    """Compute roadmap-derived fields for a single objective."""
    progress = "-"
    state = "-"
    deps_state = "-"
    deps = "-"
    next_node = "-"

    if not plan.body:
        return {
            "progress": progress,
            "state": state,
            "deps_state": deps_state,
            "deps": deps,
            "next_node": next_node,
        }

    phases, _errors = parse_roadmap(plan.body)
    if not phases:
        return {
            "progress": progress,
            "state": state,
            "deps_state": deps_state,
            "deps": deps,
            "next_node": next_node,
        }

    graph = build_graph(phases)
    summary = compute_graph_summary(graph)
    progress = f"{summary['done']}/{summary['total_nodes']}"
    state = build_state_sparkline(graph.nodes)

    next_result = find_graph_next_node(graph, phases)
    if next_result is not None:
        next_node = next_result["id"]
        min_status = graph.min_dep_status(next_result["id"])
        if min_status is None or min_status in _TERMINAL_STATUSES:
            deps_state = "ready"
        else:
            deps_state = min_status.replace("_", " ")

        # Collect blocking dep PR numbers
        target = next((n for n in graph.nodes if n.id == next_result["id"]), None)
        dep_prs: list[str] = []
        if target is not None and target.depends_on:
            node_map = {n.id: n for n in graph.nodes}
            for dep_id in target.depends_on:
                if dep_id in node_map:
                    dep = node_map[dep_id]
                    if dep.status not in _TERMINAL_STATUSES and dep.pr is not None:
                        dep_prs.append(dep.pr)

        # Also show next node's own PR if active
        if (
            target is not None
            and target.pr is not None
            and target.status not in _TERMINAL_STATUSES
            and target.pr not in set(dep_prs)
        ):
            dep_prs.append(target.pr)

        if dep_prs:
            deps = " ".join(dep_prs[:3])

    return {
        "progress": progress,
        "state": state,
        "deps_state": deps_state,
        "deps": deps,
        "next_node": next_node,
    }


@alias("ls")
@click.command("list")
@click.pass_obj
def list_objectives(ctx: ErkContext) -> None:
    """List open objectives (GitHub issues with erk-objective label)."""
    repo = discover_repo_context(ctx, ctx.cwd)

    repo_info = Ensure.not_none(ctx.repo_info, "Not in a GitHub repository")
    location = GitHubRepoLocation(
        root=repo.root,
        repo_id=GitHubRepoId(owner=repo_info.owner, repo=repo_info.name),
    )

    # Fetch objectives via dedicated service
    http_client = ctx.http_client
    if http_client is None:
        user_output(click.style("Error: ", fg="red") + "GitHub authentication not available")
        raise SystemExit(1)
    plan_data = ctx.objective_list_service.get_objective_list_data(
        location=location,
        state="open",
        limit=None,
        skip_workflow_runs=True,
        creator=None,
        http_client=http_client,
    )

    if not plan_data.plans:
        click.echo("No open objectives found.", err=True)
        return

    # Build Rich table with enriched columns matching TUI dashboard
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("slug", no_wrap=True)
    table.add_column("prog", no_wrap=True)
    table.add_column("state", no_wrap=True)
    table.add_column("deps-state", no_wrap=True)
    table.add_column("deps", no_wrap=True)
    table.add_column("next", no_wrap=True)
    table.add_column("updated", no_wrap=True)
    table.add_column("created by", no_wrap=True)

    for plan in plan_data.plans:
        slug = _compute_slug(plan)
        fields = _compute_enriched_fields(plan)
        updated = format_relative_time(plan.updated_at.isoformat()) or "-"
        author = str(plan.metadata.get("author", ""))

        table.add_row(
            f"[link={plan.url}]#{plan.plan_identifier}[/link]",
            escape(slug),
            fields["progress"],
            fields["state"],
            fields["deps_state"],
            fields["deps"],
            fields["next_node"],
            updated,
            escape(author),
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)
