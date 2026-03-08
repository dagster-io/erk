"""Command to fetch and display a single objective."""

import json
from datetime import datetime

import click
from rich.cells import cell_len
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from erk.cli.alias import alias
from erk.cli.commands.objective_helpers import get_objective_for_branch
from erk.cli.commands.pr.repo_resolution import get_remote_github, repo_option, resolve_owner_repo
from erk.cli.ensure import UserFacingCliError
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_raw_metadata_blocks,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    build_graph,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    parse_v2_roadmap,
    serialize_phases,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.output.output import user_output


def _format_field(label: str, value: str) -> str:
    """Format a field with dimmed label and consistent width.

    Uses a fixed width of 12 characters for label alignment across all
    objective view output fields.

    Args:
        label: The field label (e.g., "State", "ID")
        value: The value to display

    Returns:
        Formatted string with styled label and value
    """
    label_width = 12
    styled_label = click.style(f"{label}:".ljust(label_width), dim=True)
    return f"{styled_label} {value}"


def _format_ref_link(ref: str | None, repo_base_url: str) -> str:
    """Convert a GitHub reference like ``#6871`` into a clickable Rich link.

    Args:
        ref: Issue/PR reference (e.g., ``"#6871"``) or ``None``.
        repo_base_url: Repository URL without trailing slash
            (e.g., ``"https://github.com/owner/repo"``).

    Returns:
        Rich markup string with ``[link=...]`` wrapper, or ``"-"`` when
        *ref* is ``None``.
    """
    if ref is None:
        return "-"
    issue_number = ref.lstrip("#")
    return f"[link={repo_base_url}/issues/{issue_number}]{escape(ref)}[/link]"


def _format_node_status(status: str, *, is_unblocked: bool) -> str:
    """Format node status indicator with emoji and Rich markup.

    Args:
        status: Node status ("done", "in_progress", "planning", "pending", "blocked", "skipped")
        is_unblocked: Whether the node's dependencies are all satisfied

    Returns:
        Rich markup string with emoji and color
    """
    if status == "done":
        return "[green]✅ done[/green]"
    if status == "in_progress":
        return "[yellow]🔄 in_progress[/yellow]"
    if status == "planning":
        return "[magenta]🚀 planning[/magenta]"
    if status == "blocked":
        return "[red]🚫 blocked[/red]"
    if status == "skipped":
        return "[dim]⏭ skipped[/dim]"
    # Default: pending
    if is_unblocked:
        return "[green bold]⏳ pending (unblocked)[/green bold]"
    return "[dim]⏳ pending[/dim]"


def _extract_repo_base_url(issue_url: str) -> str:
    """Extract the repository base URL from a GitHub issue URL.

    Args:
        issue_url: Full issue URL (e.g., ``"https://github.com/owner/repo/issues/123"``)

    Returns:
        Repository base URL (e.g., ``"https://github.com/owner/repo"``)
    """
    return issue_url.rsplit("/issues/", 1)[0]


def _format_timestamp(dt_value: datetime, *, label: str) -> str:
    """Format a timestamp with relative time.

    Args:
        dt_value: Datetime value to format
        label: Field label for display

    Returns:
        Formatted string with absolute date and relative time
    """
    absolute_str = dt_value.strftime("%Y-%m-%d")
    relative_str = format_relative_time(dt_value.isoformat())
    display = f"{absolute_str} ({relative_str})" if relative_str else absolute_str
    return _format_field(label, display)


def _display_json(
    *,
    issue_number: int,
    phases: list[RoadmapPhase],
    graph: DependencyGraph,
) -> None:
    """Display JSON output for programmatic use."""
    next_node = graph.next_node()
    summary = compute_graph_summary(graph)

    # Add in_flight count (planning + in_progress)
    summary["in_flight"] = summary["planning"] + summary["in_progress"]

    output = {
        "issue_number": issue_number,
        "phases": serialize_phases(phases),
        "graph": {
            "nodes": [
                {
                    "id": n.id,
                    "slug": n.slug,
                    "description": n.description,
                    "status": n.status,
                    "pr": n.pr,
                    "depends_on": list(n.depends_on),
                }
                for n in graph.nodes
            ],
            "unblocked": [n.id for n in graph.unblocked_nodes()],
            "pending_unblocked": [n.id for n in graph.pending_unblocked_nodes()],
            "next_node": next_node.id if next_node else None,
            "is_complete": graph.is_complete(),
        },
        "summary": summary,
    }
    click.echo(json.dumps(output))


@alias("v")
@click.command("view")
@click.argument("objective_ref", type=str, required=False, default=None)
@click.option(
    "--json-output",
    "json_mode",
    is_flag=True,
    default=False,
    help="Output structured JSON for programmatic use",
)
@repo_option
@click.pass_obj
def view_objective(
    ctx: ErkContext,
    objective_ref: str | None,
    *,
    json_mode: bool,
    target_repo: str | None,
) -> None:
    """Fetch and display an objective by identifier.

    OBJECTIVE_REF can be a plain number (e.g., "42"), P-prefixed ("P42"),
    or a GitHub issue URL (e.g., "https://github.com/owner/repo/issues/123").

    If omitted, infers the objective from the current branch.
    """
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    # Resolve issue number: explicit ref or inferred from branch
    if objective_ref is not None:
        issue_number = parse_issue_identifier(objective_ref)
    else:
        if isinstance(ctx.repo, NoRepoSentinel):
            raise UserFacingCliError(
                "No objective reference provided and no local repository.\n"
                "Usage: erk objective view <objective_ref>"
            )
        branch = ctx.git.branch.get_current_branch(ctx.repo.root)
        if branch is None:
            raise UserFacingCliError(
                "No objective reference provided and not on a branch.\n"
                "Usage: erk objective view <objective_ref>"
            )
        objective_id = get_objective_for_branch(ctx, ctx.repo.root, branch)
        if objective_id is None:
            raise UserFacingCliError(
                f"No objective reference provided and branch '{branch}' "
                "is not linked to an objective.\n"
                "Usage: erk objective view <objective_ref>"
            )
        issue_number = objective_id

    # Fetch issue from GitHub
    result = remote.get_issue(owner=owner, repo=repo_name, number=issue_number)
    if isinstance(result, IssueNotFound):
        raise UserFacingCliError(f"Issue #{issue_number} not found")
    issue = result

    # Verify erk-objective label
    if "erk-objective" not in issue.labels:
        raise UserFacingCliError(
            f"Issue #{issue_number} is not an objective (missing erk-objective label)"
        )

    # Parse roadmap from issue body (v2 format only)
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    has_roadmap_block = any(b.key == BlockKeys.OBJECTIVE_ROADMAP for b in raw_blocks)

    if has_roadmap_block:
        v2_result = parse_v2_roadmap(issue.body)
        if v2_result is None:
            raise UserFacingCliError(
                "This objective uses a legacy format that is no longer supported. "
                "To migrate, open Claude Code and use /erk:objective-create to "
                "recreate this objective with the same content."
            )
        phases, _validation_errors = v2_result
    else:
        phases = []

    # Build graph and compute summary statistics
    graph = build_graph(phases)
    summary = compute_graph_summary(graph)

    # JSON output mode
    if json_mode:
        _display_json(
            issue_number=issue_number,
            phases=phases,
            graph=graph,
        )
        return

    # Build node lookup and compute unblocked set
    node_by_id: dict[str, ObjectiveNode] = {n.id: n for n in graph.nodes}
    unblocked_ids = {n.id for n in graph.unblocked_nodes()}

    # Find next node
    next_node = find_graph_next_node(graph, phases)

    # Display objective details
    user_output("")
    user_output(_format_field("Title", click.style(issue.title, bold=True)))

    # Display metadata with clickable ID
    state_color = "green" if issue.state == "OPEN" else "red"
    user_output(_format_field("State", click.style(issue.state, fg=state_color)))

    # Make ID clickable using OSC 8
    id_text = f"#{issue_number}"
    colored_id = click.style(id_text, fg="cyan")
    clickable_id = f"\033]8;;{issue.url}\033\\{colored_id}\033]8;;\033\\"
    user_output(_format_field("ID", clickable_id))
    user_output(_format_field("URL", issue.url))

    # Display timestamps with relative time
    user_output(_format_timestamp(issue.created_at, label="Created"))
    user_output(_format_timestamp(issue.updated_at, label="Updated"))

    # Derive repo base URL for linkifying references
    repo_base_url = _extract_repo_base_url(issue.url)

    # Display roadmap if phases exist
    if phases:
        user_output("")
        user_output(click.style("─── Roadmap ───", bold=True))

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
                node = node_by_id.get(step.id)
                is_unblocked = step.id in unblocked_ids
                status_markup = _format_node_status(step.status, is_unblocked=is_unblocked)
                max_status_width = max(
                    max_status_width,
                    cell_len(Text.from_markup(status_markup).plain),
                )
                max_desc_width = max(max_desc_width, cell_len(step.description))
                deps_str = ", ".join(node.depends_on) if node and node.depends_on else "-"
                max_deps_width = max(max_deps_width, cell_len(deps_str))
                max_pr_width = max(max_pr_width, cell_len("-" if step.pr is None else step.pr))

        for phase in phases:
            # Count done steps in this phase
            done_count = sum(1 for step in phase.nodes if step.status == "done")
            total_count = len(phase.nodes)

            # Format phase identifier (e.g., "Phase 1A" or "Phase 1")
            phase_id = f"Phase {phase.number}{phase.suffix}"

            # Format phase header
            phase_header = f"{phase_id}: {phase.name} ({done_count}/{total_count} nodes done)"
            user_output(click.style(phase_header, bold=True))

            # Display steps as a Rich table for proper alignment
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
        user_output(click.style("─── Summary ───", bold=True))

        # Format steps summary (include planning count)
        nodes_parts = [
            f"{summary['done']}/{summary['total_nodes']} done",
        ]
        if summary["planning"] > 0:
            nodes_parts.append(f"{summary['planning']} planning")
        nodes_parts.append(f"{summary['in_progress']} in progress")
        nodes_parts.append(f"{summary['pending']} pending")
        user_output(_format_field("Nodes", ", ".join(nodes_parts)))

        # Display in-flight count (planning + in_progress)
        in_flight = summary["planning"] + summary["in_progress"]
        user_output(_format_field("In flight", str(in_flight)))

        # Display unblocked count
        pending_unblocked = graph.pending_unblocked_nodes()
        user_output(_format_field("Unblocked", str(len(pending_unblocked))))

        # Display next nodes - show all unblocked pending when multiple
        if len(pending_unblocked) > 1:
            # Multiple unblocked: list them all
            # Find phase for each node
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
                    # Indent continuation lines to align with the first value
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

    else:
        # No roadmap found
        user_output("")
        user_output(click.style("─── Roadmap ───", bold=True))
        user_output(click.style("No roadmap data found", dim=True))
