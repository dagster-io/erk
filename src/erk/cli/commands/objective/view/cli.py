"""Human command for objective view with rich terminal output."""

import json

import click
from rich.cells import cell_len
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from erk.cli.commands.objective.view.operation import (
    ObjectiveViewRequest,
    ObjectiveViewResult,
    run_objective_view,
)
from erk.cli.ensure import UserFacingCliError
from erk.cli.repo_resolution import resolved_repo_option
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.cli_alias import alias
from erk_shared.gateway.github.metadata.dependency_graph import (
    ObjectiveNode,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.output.output import user_output


def _format_field(label: str, value: str) -> str:
    """Format a field with dimmed label and consistent width."""
    label_width = 12
    styled_label = click.style(f"{label}:".ljust(label_width), dim=True)
    return f"{styled_label} {value}"


def _format_ref_link(ref: str | None, repo_base_url: str) -> str:
    """Convert a GitHub reference like ``#6871`` into a clickable Rich link."""
    if ref is None:
        return "-"
    issue_number = ref.lstrip("#")
    return f"[link={repo_base_url}/issues/{issue_number}]{escape(ref)}[/link]"


def _format_node_status(status: str, *, is_unblocked: bool) -> str:
    """Format node status indicator with emoji and Rich markup."""
    if status == "done":
        return "[green]\u2705 done[/green]"
    if status == "in_progress":
        return "[yellow]\U0001f504 in_progress[/yellow]"
    if status == "planning":
        return "[magenta]\U0001f680 planning[/magenta]"
    if status == "blocked":
        return "[red]\U0001f6ab blocked[/red]"
    if status == "skipped":
        return "[dim]\u23ed skipped[/dim]"
    # Default: pending
    if is_unblocked:
        return "[green bold]\u23f3 pending (unblocked)[/green bold]"
    return "[dim]\u23f3 pending[/dim]"


@alias("v")
@click.command("view")
@click.argument("objective_ref", type=str, required=False, default=None)
@click.option(
    "--json-output",
    "json_mode",
    is_flag=True,
    default=False,
    help="[Deprecated: use 'erk json objective view'] Output structured JSON",
)
@resolved_repo_option
@click.pass_obj
def view_objective(
    ctx: ErkContext,
    objective_ref: str | None,
    *,
    json_mode: bool,
    repo_id: GitHubRepoId,
) -> None:
    """Fetch and display an objective by identifier.

    OBJECTIVE_REF can be a plain number (e.g., "42"), P-prefixed ("P42"),
    or a GitHub issue URL (e.g., "https://github.com/owner/repo/issues/123").

    If omitted, infers the objective from the current branch.
    """
    request = ObjectiveViewRequest(identifier=objective_ref)
    result = run_objective_view(ctx, request, repo_id=repo_id)

    if isinstance(result, MachineCommandError):
        raise UserFacingCliError(result.message, error_type=result.error_type)

    if json_mode:
        click.echo(json.dumps(result.to_json_dict()))
        return

    _render_human(result)


def _render_human(result: ObjectiveViewResult) -> None:
    """Render objective view with rich terminal output."""
    issue = result.issue

    user_output("")
    user_output(_format_field("Title", click.style(issue.title, bold=True)))

    state_color = "green" if issue.state == "OPEN" else "red"
    user_output(_format_field("State", click.style(issue.state, fg=state_color)))

    id_text = f"#{result.issue_number}"
    colored_id = click.style(id_text, fg="cyan")
    clickable_id = f"\033]8;;{issue.url}\033\\{colored_id}\033]8;;\033\\"
    user_output(_format_field("ID", clickable_id))
    user_output(_format_field("URL", issue.url))

    for dt_value, label in [(issue.created_at, "Created"), (issue.updated_at, "Updated")]:
        absolute_str = dt_value.strftime("%Y-%m-%d")
        relative_str = format_relative_time(dt_value.isoformat())
        display = f"{absolute_str} ({relative_str})" if relative_str else absolute_str
        user_output(_format_field(label, display))

    repo_base_url = issue.url.rsplit("/issues/", 1)[0]

    if result.phases:
        _render_roadmap(result, repo_base_url=repo_base_url)
    else:
        user_output("")
        user_output(click.style("\u2500\u2500\u2500 Roadmap \u2500\u2500\u2500", bold=True))
        user_output(click.style("No roadmap data found", dim=True))


def _render_roadmap(result: ObjectiveViewResult, *, repo_base_url: str) -> None:
    """Render the roadmap with Rich tables."""
    phases = result.phases
    graph = result.graph
    summary = compute_graph_summary(graph)
    node_by_id: dict[str, ObjectiveNode] = {n.id: n for n in graph.nodes}
    unblocked_ids = {n.id for n in graph.unblocked_nodes()}
    next_node = find_graph_next_node(graph, phases)

    user_output("")
    user_output(click.style("\u2500\u2500\u2500 Roadmap \u2500\u2500\u2500", bold=True))

    console = Console(stderr=True, force_terminal=True)

    # Pre-compute max column widths across all phases for global alignment
    max_id_width = 0
    max_status_width = 0
    max_desc_width = 0
    max_deps_width = 0
    max_pr_width = 0
    for phase in phases:
        for step in phase.nodes:
            max_id_width = max(max_id_width, cell_len(step.id))
            is_unblocked = step.id in unblocked_ids
            status_markup = _format_node_status(step.status, is_unblocked=is_unblocked)
            max_status_width = max(
                max_status_width,
                cell_len(Text.from_markup(status_markup).plain),
            )
            max_desc_width = max(max_desc_width, cell_len(step.description))
            node = node_by_id.get(step.id)
            deps_str = ", ".join(node.depends_on) if node and node.depends_on else "-"
            max_deps_width = max(max_deps_width, cell_len(deps_str))
            max_pr_width = max(max_pr_width, cell_len("-" if step.pr is None else step.pr))

    for phase in phases:
        done_count = sum(1 for step in phase.nodes if step.status == "done")
        total_count = len(phase.nodes)

        phase_id = f"Phase {phase.number}{phase.suffix}"
        phase_header = f"{phase_id}: {phase.name} ({done_count}/{total_count} nodes done)"
        user_output(click.style(phase_header, bold=True))

        table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            pad_edge=False,
            padding=(0, 1),
        )
        table.add_column("node", style="cyan", no_wrap=True, min_width=max_id_width)
        table.add_column("status", no_wrap=True, min_width=max_status_width)
        table.add_column("description", min_width=max_desc_width)
        table.add_column("depends_on", style="dim", min_width=max_deps_width)
        table.add_column("pr", no_wrap=True, min_width=max_pr_width)

        for step in phase.nodes:
            node = node_by_id.get(step.id)
            is_unblocked = step.id in unblocked_ids
            deps_str = ", ".join(node.depends_on) if node and node.depends_on else "-"
            table.add_row(
                escape(step.id),
                _format_node_status(step.status, is_unblocked=is_unblocked),
                escape(step.description),
                escape(deps_str),
                _format_ref_link(step.pr, repo_base_url),
            )

        console.print(table)
        user_output("")

    # Display summary
    user_output(click.style("\u2500\u2500\u2500 Summary \u2500\u2500\u2500", bold=True))

    nodes_parts = [f"{summary['done']}/{summary['total_nodes']} done"]
    if summary["planning"] > 0:
        nodes_parts.append(f"{summary['planning']} planning")
    nodes_parts.append(f"{summary['in_progress']} in progress")
    nodes_parts.append(f"{summary['pending']} pending")
    user_output(_format_field("Nodes", ", ".join(nodes_parts)))

    in_flight = summary["planning"] + summary["in_progress"]
    user_output(_format_field("In flight", str(in_flight)))

    pending_unblocked = graph.pending_unblocked_nodes()
    user_output(_format_field("Unblocked", str(len(pending_unblocked))))

    if len(pending_unblocked) > 1:
        phase_by_node: dict[str, str] = {}
        for phase in phases:
            for step in phase.nodes:
                phase_by_node[step.id] = f"Phase {phase.number}{phase.suffix}"
        first = True
        for node in pending_unblocked:
            phase_label = phase_by_node.get(node.id, "")
            line = f"{node.id} - {node.description} ({phase_label})"
            if first:
                user_output(_format_field("Next nodes", line))
                first = False
            else:
                user_output(f"{'':>14}{line}")
    elif next_node:
        user_output(
            _format_field(
                "Next node",
                f"{next_node['id']} - {next_node['description']} (Phase: {next_node['phase']})",
            )
        )
    else:
        user_output(_format_field("Next node", "None"))
