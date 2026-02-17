"""Inspect an objective's dependency graph and show actionable state."""

import json

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext, RepoContext
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    compute_graph_summary,
    graph_from_phases,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    parse_v2_roadmap,
    serialize_phases,
)
from erk_shared.output.output import user_output


def _format_node_status(node: ObjectiveNode, *, is_unblocked: bool) -> str:
    """Format node status with graph-aware annotations.

    Args:
        node: The objective node
        is_unblocked: Whether the node's dependencies are satisfied

    Returns:
        Rich markup string with emoji and color
    """
    status = node.status
    if status == "done":
        return "[green]done[/green]"
    if status == "skipped":
        return "[dim]skipped[/dim]"
    if status == "in_progress":
        ref_text = f" ({escape(node.plan)})" if node.plan else ""
        return f"[yellow]in_progress{ref_text}[/yellow]"
    if status == "blocked":
        return "[red]blocked[/red]"
    if status == "planning":
        ref_text = f" ({escape(node.pr)})" if node.pr else ""
        return f"[cyan]planning{ref_text}[/cyan]"
    # pending
    if is_unblocked:
        return "[green bold]pending (unblocked)[/green bold]"
    return "[dim]pending[/dim]"


def _display_human(
    *,
    issue_title: str,
    issue_number: int,
    issue_state: str,
    phases: list[RoadmapPhase],
    graph: DependencyGraph,
) -> None:
    """Display human-readable graph inspection output."""
    unblocked_ids = {n.id for n in graph.unblocked_nodes()}
    next_node = graph.next_node()
    summary = compute_graph_summary(graph)
    node_by_id = {n.id: n for n in graph.nodes}

    # Header
    user_output("")
    state_color = "green" if issue_state == "OPEN" else "red"
    user_output(
        click.style(f"Objective #{issue_number}: ", dim=True)
        + click.style(issue_title, bold=True)
        + "  "
        + click.style(f"[{issue_state}]", fg=state_color)
    )

    # Roadmap with graph annotations
    user_output("")
    user_output(click.style("─── Dependency Graph ───", bold=True))

    console = Console(stderr=True, force_terminal=True)

    for phase in phases:
        done_count = sum(1 for s in phase.steps if s.status == "done")
        total_count = len(phase.steps)
        phase_id = f"Phase {phase.number}{phase.suffix}"
        phase_label = f"{phase_id}: {phase.name} ({done_count}/{total_count})"
        user_output(click.style(phase_label, bold=True))

        table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            pad_edge=False,
            padding=(0, 1),
        )
        table.add_column("node", style="cyan", no_wrap=True)
        table.add_column("status", no_wrap=True)
        table.add_column("description")
        table.add_column("depends_on", style="dim")
        table.add_column("plan", no_wrap=True)
        table.add_column("pr", no_wrap=True)

        for step in phase.steps:
            # Find the corresponding graph node
            node = node_by_id.get(step.id)
            if node is None:
                continue

            is_unblocked = node.id in unblocked_ids
            deps_str = ", ".join(node.depends_on) if node.depends_on else "-"

            table.add_row(
                escape(node.id),
                _format_node_status(node, is_unblocked=is_unblocked),
                escape(node.description),
                deps_str,
                escape(node.plan) if node.plan else "-",
                escape(node.pr) if node.pr else "-",
            )

        console.print(table)
        user_output("")

    # Summary
    user_output(click.style("─── Summary ───", bold=True))
    user_output(
        click.style("Steps:       ", dim=True)
        + f"{summary['done']}/{summary['total_steps']} done, "
        + f"{summary['in_progress']} in progress, "
        + f"{summary['pending']} pending"
    )

    unblocked_pending = [n for n in graph.unblocked_nodes() if n.status == "pending"]
    user_output(click.style("Unblocked:   ", dim=True) + str(len(unblocked_pending)))

    if graph.is_complete():
        user_output(click.style("Complete:    ", dim=True) + click.style("Yes", fg="green"))
    elif next_node is not None:
        user_output(
            click.style("Next node:   ", dim=True)
            + click.style(next_node.id, bold=True)
            + f" - {next_node.description}"
        )
    else:
        user_output(click.style("Next node:   ", dim=True) + "None")


def _display_json(
    *,
    issue_number: int,
    phases: list[RoadmapPhase],
    graph: DependencyGraph,
) -> None:
    """Display JSON output for programmatic use."""
    next_node = graph.next_node()
    summary = compute_graph_summary(graph)

    output = {
        "issue_number": issue_number,
        "phases": serialize_phases(phases),
        "graph": {
            "nodes": [
                {
                    "id": n.id,
                    "description": n.description,
                    "status": n.status,
                    "plan": n.plan,
                    "pr": n.pr,
                    "depends_on": list(n.depends_on),
                }
                for n in graph.nodes
            ],
            "unblocked": [n.id for n in graph.unblocked_nodes()],
            "next_node": next_node.id if next_node else None,
            "is_complete": graph.is_complete(),
        },
        "summary": summary,
    }
    click.echo(json.dumps(output))


@alias("i")
@click.command("inspect")
@click.argument("objective_ref", type=str)
@click.option(
    "--json-output",
    "json_mode",
    is_flag=True,
    default=False,
    help="Output structured JSON for programmatic use",
)
@click.pass_obj
def inspect_objective(ctx: ErkContext, objective_ref: str, *, json_mode: bool) -> None:
    """Inspect an objective's dependency graph and actionable state.

    OBJECTIVE_REF can be an issue number (42) or a full GitHub URL.

    Shows the roadmap as a dependency graph with unblocked nodes highlighted
    and the recommended next node to work on.

    \b
    Examples:
      erk objective inspect 42
      erk objective inspect 42 --json-output
    """
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    issue_number = parse_issue_identifier(objective_ref)

    # Fetch issue
    result = ctx.issues.get_issue(repo.root, issue_number)
    if isinstance(result, IssueNotFound):
        raise click.ClickException(f"Issue #{issue_number} not found")
    issue = result

    # Verify label
    if "erk-objective" not in issue.labels:
        raise click.ClickException(
            f"Issue #{issue_number} is not an objective (missing erk-objective label)"
        )

    # Parse roadmap
    v2_result = parse_v2_roadmap(issue.body)
    if v2_result is None:
        raise click.ClickException(
            "This objective uses a legacy format that is no longer supported."
        )
    phases, _validation_errors = v2_result

    # Build dependency graph
    graph = graph_from_phases(phases)

    if json_mode:
        _display_json(
            issue_number=issue_number,
            phases=phases,
            graph=graph,
        )
    else:
        _display_human(
            issue_title=issue.title,
            issue_number=issue_number,
            issue_state=issue.state,
            phases=phases,
            graph=graph,
        )
