"""Dependency graph representation for objective roadmaps.

Provides ObjectiveNode and DependencyGraph types that model step dependencies
explicitly, plus a graph_from_phases() parser that infers sequential dependencies
from existing RoadmapPhase/RoadmapStep data.

Phase 1 of Objective #7242: these types coexist alongside the existing
RoadmapStep/RoadmapPhase types. Phase 2 will migrate callers.
"""

from collections import Counter
from dataclasses import dataclass

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    RoadmapStep,
    RoadmapStepStatus,
    group_steps_by_phase,
    parse_v2_roadmap,
)

_TERMINAL_STATUSES: set[RoadmapStepStatus] = {"done", "skipped"}


@dataclass(frozen=True)
class ObjectiveNode:
    """A node in the objective dependency graph."""

    id: str
    description: str
    status: RoadmapStepStatus
    plan: str | None
    pr: str | None
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class DependencyGraph:
    """A directed acyclic graph of objective nodes with dependency edges."""

    nodes: tuple[ObjectiveNode, ...]

    def _node_map(self) -> dict[str, ObjectiveNode]:
        return {node.id: node for node in self.nodes}

    def unblocked_nodes(self) -> list[ObjectiveNode]:
        """Nodes whose dependencies are all satisfied (done or skipped)."""
        node_map = self._node_map()
        result: list[ObjectiveNode] = []
        for node in self.nodes:
            all_satisfied = all(
                node_map[dep_id].status in _TERMINAL_STATUSES
                for dep_id in node.depends_on
                if dep_id in node_map
            )
            if all_satisfied:
                result.append(node)
        return result

    def next_node(self) -> ObjectiveNode | None:
        """First unblocked pending node by position order. None if no pending nodes."""
        for node in self.unblocked_nodes():
            if node.status == "pending":
                return node
        return None

    def is_complete(self) -> bool:
        """True if every node is done or skipped."""
        return all(node.status in _TERMINAL_STATUSES for node in self.nodes)


def graph_from_phases(phases: list[RoadmapPhase]) -> DependencyGraph:
    """Convert phases into a DependencyGraph, inferring sequential dependencies.

    Dependency rules:
    - First step in a phase: depends on last step of previous phase (if any)
    - Subsequent steps in a phase: depends on previous step in same phase
    """
    nodes: list[ObjectiveNode] = []
    last_step_id_of_prev_phase: str | None = None

    for phase in phases:
        prev_step_id: str | None = None

        for i, step in enumerate(phase.steps):
            if i == 0 and last_step_id_of_prev_phase is not None:
                depends_on = (last_step_id_of_prev_phase,)
            elif prev_step_id is not None:
                depends_on = (prev_step_id,)
            else:
                depends_on = ()

            nodes.append(
                ObjectiveNode(
                    id=step.id,
                    description=step.description,
                    status=step.status,
                    plan=step.plan,
                    pr=step.pr,
                    depends_on=depends_on,
                )
            )
            prev_step_id = step.id

        if phase.steps:
            last_step_id_of_prev_phase = phase.steps[-1].id

    return DependencyGraph(nodes=tuple(nodes))


def steps_from_graph(graph: DependencyGraph) -> list[RoadmapStep]:
    """Convert graph nodes to flat RoadmapStep list (inverse of the flatten in graph_from_phases).

    Strips dependency information, returning plain steps suitable for
    serialization to YAML frontmatter via render_roadmap_block_inner().
    """
    return [
        RoadmapStep(
            id=node.id,
            description=node.description,
            status=node.status,
            plan=node.plan,
            pr=node.pr,
        )
        for node in graph.nodes
    ]


def phases_from_graph(graph: DependencyGraph) -> list[RoadmapPhase]:
    """Convert graph back to phases (inverse of graph_from_phases).

    Phase names are placeholders — use enrich_phase_names() to restore from body text.
    """
    return group_steps_by_phase(steps_from_graph(graph))


def compute_graph_summary(graph: DependencyGraph) -> dict[str, int]:
    """Compute summary statistics from graph nodes directly.

    Returns the same dict format as compute_summary(phases).
    """
    counts = Counter(node.status for node in graph.nodes)
    return {
        "total_nodes": len(graph.nodes),
        "pending": counts.get("pending", 0),
        "planning": counts.get("planning", 0),
        "done": counts.get("done", 0),
        "in_progress": counts.get("in_progress", 0),
        "blocked": counts.get("blocked", 0),
        "skipped": counts.get("skipped", 0),
    }


def _find_node_by_status(
    nodes: tuple[ObjectiveNode, ...], status: RoadmapStepStatus
) -> ObjectiveNode | None:
    """Find the first node with the given status, or None."""
    return next((node for node in nodes if node.status == status), None)


def find_graph_next_node(
    graph: DependencyGraph, phases: list[RoadmapPhase]
) -> dict[str, str] | None:
    """Find the next actionable node by graph order, returning the dict format needed by JSON APIs.

    Tries pending nodes first, then falls back to in_progress nodes. This ensures
    objectives with only in_progress remaining steps still show a "next step" in the
    TUI and JSON APIs, rather than returning None.

    For dependency-aware selection (only unblocked nodes), use graph.next_node() directly.

    Args:
        graph: The dependency graph
        phases: Phases for phase name lookup

    Returns:
        Dict with {id, description, phase} or None if no pending or in_progress nodes.
    """
    target_node = _find_node_by_status(graph.nodes, "pending")
    if target_node is None:
        target_node = _find_node_by_status(graph.nodes, "in_progress")
    if target_node is None:
        return None

    # Find the phase containing this node
    phase_name = next(
        (phase.name for phase in phases if any(step.id == target_node.id for step in phase.steps)),
        "",
    )

    return {
        "id": target_node.id,
        "description": target_node.description,
        "phase": phase_name,
    }


def parse_graph(body: str) -> tuple[DependencyGraph, list[RoadmapPhase], list[str]] | None:
    """Parse a v2 roadmap body into both graph and phases.

    Convenience function combining parse_v2_roadmap + graph_from_phases.
    Most callers need both graph (for logic) and phases (for display grouping).

    Args:
        body: Full objective body text with metadata blocks and markdown headers.

    Returns:
        (graph, enriched_phases, errors) or None if body is not v2 format.
    """
    v2_result = parse_v2_roadmap(body)
    if v2_result is None:
        return None
    phases, errors = v2_result
    graph = graph_from_phases(phases)
    return (graph, phases, errors)
