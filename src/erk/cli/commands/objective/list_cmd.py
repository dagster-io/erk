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
    DependencyGraph,
    ObjectiveNode,
    build_graph,
    build_state_sparkline,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.roadmap import RoadmapPhase, parse_roadmap
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan

_SLUG_MAX_LEN = 30


def _compute_slug(plan: Plan) -> str:
    if plan.body:
        slug = extract_objective_slug(plan.body)
        if slug is not None:
            return slug[:_SLUG_MAX_LEN]
    if plan.title:
        return plan.title.removeprefix("Objective: ")[:_SLUG_MAX_LEN]
    return "-"


def _collect_blocking_dep_prs(
    graph: DependencyGraph,
    target: ObjectiveNode | None,
) -> list[str]:
    """Collect PR numbers from blocking (non-terminal) dependencies of a node."""
    if target is None or not target.depends_on:
        return []
    node_map = {n.id: n for n in graph.nodes}
    prs: list[str] = []
    for dep_id in target.depends_on:
        dep = node_map.get(dep_id)
        if dep is not None and dep.status not in _TERMINAL_STATUSES and dep.pr is not None:
            prs.append(dep.pr)
    return prs


def _compute_next_node_fields(
    graph: DependencyGraph,
    phases: list[RoadmapPhase],
) -> tuple[str, str, str]:
    """Compute next-node, deps-state, and deps fields from a dependency graph.

    Returns:
        (next_node, deps_state, deps) tuple with display strings.
    """
    next_result = find_graph_next_node(graph, phases)
    if next_result is None:
        return ("-", "-", "-")

    next_node = next_result["id"]
    min_status = graph.min_dep_status(next_result["id"])
    if min_status is None or min_status in _TERMINAL_STATUSES:
        deps_state = "ready"
    else:
        deps_state = min_status.replace("_", " ")

    # Collect blocking dep PR numbers
    target = next((n for n in graph.nodes if n.id == next_result["id"]), None)
    dep_prs: list[str] = _collect_blocking_dep_prs(graph, target)

    # Also show next node's own PR if active
    if (
        target is not None
        and target.pr is not None
        and target.status not in _TERMINAL_STATUSES
        and target.pr not in set(dep_prs)
    ):
        dep_prs.append(target.pr)

    deps = " ".join(dep_prs[:3]) if dep_prs else "-"
    return (next_node, deps_state, deps)


_SPARKLINE_RICH_STYLES: dict[str, str] = {
    "✓": "[green]✓[/green]",
    "▶": "[yellow]▶[/yellow]",
    "◐": "[blue]◐[/blue]",
    "○": "[dim]○[/dim]",
    "⊘": "[red]⊘[/red]",
    "-": "[dim]-[/dim]",
}


def _rich_sparkline(sparkline: str) -> str:
    """Wrap sparkline characters in Rich markup for colored output."""
    return "".join(_SPARKLINE_RICH_STYLES.get(ch, ch) for ch in sparkline)


def _compute_enriched_fields(plan: Plan) -> dict[str, str]:
    """Compute roadmap-derived fields for a single objective."""
    defaults = {
        "progress": "-",
        "state": "-",
        "deps_state": "-",
        "deps": "-",
        "next_node": "-",
    }

    if not plan.body:
        return defaults

    phases, _errors = parse_roadmap(plan.body)
    if not phases:
        return defaults

    graph = build_graph(phases)
    summary = compute_graph_summary(graph)
    next_node, deps_state, deps = _compute_next_node_fields(graph, phases)

    return {
        "progress": f"{summary['done']}/{summary['total_nodes']}",
        "state": build_state_sparkline(graph.nodes),
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
    table.add_column("slug", no_wrap=True, min_width=20)
    table.add_column("prog", no_wrap=True)
    table.add_column("state", no_wrap=True)
    table.add_column("deps-state", no_wrap=True, min_width=10)
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
            _rich_sparkline(fields["state"]),
            fields["deps_state"],
            fields["deps"],
            fields["next_node"],
            updated,
            escape(author),
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)
