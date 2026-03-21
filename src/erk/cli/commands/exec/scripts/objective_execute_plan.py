"""Resolve the next N nodes from an objective's dependency graph in execution order.

Dry-run / preview only — no dispatch or mutation.

Usage:
    erk exec objective-execute-plan <objective_number> --count N [--json]

Output:
    Text or JSON execution plan showing which nodes would be dispatched next.

Exit Codes:
    0: Success
    1: Error (not found, validation error, no pending nodes)
"""

import json

import click

from erk.cli.commands.objective.check.validation import (
    ObjectiveValidationError,
    validate_objective,
)
from erk.cli.repo_resolution import get_remote_github
from erk_shared.context.helpers import require_context
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.metadata.dependency_graph import (
    ObjectiveNode,
    phases_from_graph,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    enrich_phase_names,
)


def _find_phase_name(phases: list[RoadmapPhase], node_id: str) -> str:
    """Return the phase name containing node_id, or empty string if not found."""
    return next(
        (phase.name for phase in phases if any(n.id == node_id for n in phase.nodes)),
        "",
    )


def _build_node_dict(
    position: int, node: ObjectiveNode, phase_name: str
) -> dict[str, object]:
    return {
        "position": position,
        "id": node.id,
        "description": node.description,
        "phase": phase_name,
        "slug": node.slug or "",
    }


@click.command(name="objective-execute-plan")
@click.argument("objective_number", type=int)
@click.option("--count", type=int, required=True, help="Number of nodes to resolve")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON")
@click.pass_context
def objective_execute_plan(
    ctx: click.Context,
    objective_number: int,
    count: int,
    output_json: bool,
) -> None:
    """Resolve the next N nodes from an objective's dependency graph.

    OBJECTIVE_NUMBER is the GitHub issue number of the objective.

    Simulates sequential execution: completing each selected node unblocks the
    next dependent node. Output is a preview only — no dispatch or mutations.

    \b
    Examples:
      erk exec objective-execute-plan 42 --count 3
      erk exec objective-execute-plan 42 --count 5 --json
    """
    erk_ctx = require_context(ctx)

    if isinstance(erk_ctx.repo, NoRepoSentinel) or erk_ctx.repo.github is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "no_repo",
                    "message": "Cannot determine owner/repo from current context",
                }
            )
        )
        raise SystemExit(1)

    owner = erk_ctx.repo.github.owner
    repo_name = erk_ctx.repo.github.repo
    remote = get_remote_github(erk_ctx)

    validation_result = validate_objective(
        remote,
        owner=owner,
        repo=repo_name,
        issue_number=objective_number,
    )

    if isinstance(validation_result, ObjectiveValidationError):
        if output_json:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": validation_result.error,
                    }
                )
            )
        else:
            click.echo(f"Error: {validation_result.error}", err=True)
        raise SystemExit(1)

    graph = validation_result.graph

    if not graph.nodes:
        if output_json:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "no_roadmap",
                        "message": f"Objective #{objective_number} has no roadmap",
                    }
                )
            )
        else:
            click.echo(f"Objective #{objective_number} has no roadmap.", err=True)
        raise SystemExit(1)

    total_pending = sum(1 for node in graph.nodes if node.status == "pending")

    resolved_nodes = graph.simulate_next_n(count=count)

    phases = phases_from_graph(graph)
    phases = enrich_phase_names(validation_result.issue_body, phases)

    if output_json:
        node_dicts = [
            _build_node_dict(i + 1, node, _find_phase_name(phases, node.id))
            for i, node in enumerate(resolved_nodes)
        ]
        click.echo(
            json.dumps(
                {
                    "objective": objective_number,
                    "nodes": node_dicts,
                    "total_pending": total_pending,
                    "requested": count,
                    "resolved": len(resolved_nodes),
                }
            )
        )
    else:
        resolved_count = len(resolved_nodes)
        click.echo(
            f"Execution plan for objective #{objective_number} "
            f"({resolved_count} of {count} requested nodes resolved):"
        )
        click.echo("")
        for i, node in enumerate(resolved_nodes):
            phase_name = _find_phase_name(phases, node.id)
            click.echo(f"  {i + 1}. [{node.id}] {node.description} (Phase: {phase_name})")
