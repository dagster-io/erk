"""Dependency graph representation for objective roadmaps.

Provides ObjectiveNode and DependencyGraph types that model node dependencies
explicitly, plus a graph_from_phases() parser that infers sequential dependencies
from existing RoadmapPhase/RoadmapNode data.
"""

from collections import Counter
from dataclasses import dataclass

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapNode,
    RoadmapNodeStatus,
    RoadmapPhase,
    group_nodes_by_phase,
    parse_v2_roadmap,
)

_TERMINAL_STATUSES: set[RoadmapNodeStatus] = {"done", "skipped"}

_STATUS_ORDER: dict[RoadmapNodeStatus, int] = {
    "pending": 0,
    "blocked": 1,
    "planning": 2,
    "in_progress": 3,
    "done": 4,
    "skipped": 4,
}

_STATUS_SYMBOLS: dict[RoadmapNodeStatus, str] = {
    "done": "✓",
    "in_progress": "▶",
    "planning": "▶",
    "pending": "○",
    "blocked": "⊘",
    "skipped": "-",
}


@dataclass(frozen=True)
class ObjectiveNode:
    """A node in the objective dependency graph."""

    id: str
    description: str
    status: RoadmapNodeStatus
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

    def pending_unblocked_nodes(self) -> list[ObjectiveNode]:
        """All unblocked nodes with pending status, in position order."""
        return [node for node in self.unblocked_nodes() if node.status == "pending"]

    def min_dep_status(self, node_id: str) -> RoadmapNodeStatus | None:
        """Lowest status among a node's upstream dependencies.

        Returns None when the node has no dependencies or node_id is not found.
        """
        node_map = self._node_map()
        if node_id not in node_map:
            return None
        deps = node_map[node_id].depends_on
        if not deps:
            return None
        statuses = [node_map[dep_id].status for dep_id in deps if dep_id in node_map]
        if not statuses:
            return None
        return min(statuses, key=lambda s: _STATUS_ORDER.get(s, 0))

    def next_node(self) -> ObjectiveNode | None:
        """First unblocked pending node by position order. None if no pending nodes."""
        nodes = self.pending_unblocked_nodes()
        if nodes:
            return nodes[0]
        return None

    def is_complete(self) -> bool:
        """True if every node is done or skipped."""
        return all(node.status in _TERMINAL_STATUSES for node in self.nodes)


def graph_from_phases(phases: list[RoadmapPhase]) -> DependencyGraph:
    """Convert phases into a DependencyGraph, inferring sequential dependencies.

    Dependency rules:
    - First node in a phase: depends on last node of previous phase (if any)
    - Subsequent nodes in a phase: depends on previous node in same phase
    """
    nodes: list[ObjectiveNode] = []
    last_node_id_of_prev_phase: str | None = None

    for phase in phases:
        prev_node_id: str | None = None

        for i, roadmap_node in enumerate(phase.nodes):
            if i == 0 and last_node_id_of_prev_phase is not None:
                depends_on = (last_node_id_of_prev_phase,)
            elif prev_node_id is not None:
                depends_on = (prev_node_id,)
            else:
                depends_on = ()

            nodes.append(
                ObjectiveNode(
                    id=roadmap_node.id,
                    description=roadmap_node.description,
                    status=roadmap_node.status,
                    plan=roadmap_node.plan,
                    pr=roadmap_node.pr,
                    depends_on=depends_on,
                )
            )
            prev_node_id = roadmap_node.id

        if phase.nodes:
            last_node_id_of_prev_phase = phase.nodes[-1].id

    return DependencyGraph(nodes=tuple(nodes))


def graph_from_nodes(nodes: list[RoadmapNode]) -> DependencyGraph:
    """Build DependencyGraph from nodes with explicit depends_on fields.

    Uses node.depends_on directly instead of inferring from phase ordering.
    Nodes with depends_on=None are treated as having no dependencies.
    """
    return DependencyGraph(
        nodes=tuple(
            ObjectiveNode(
                id=node.id,
                description=node.description,
                status=node.status,
                plan=node.plan,
                pr=node.pr,
                depends_on=node.depends_on if node.depends_on is not None else (),
            )
            for node in nodes
        )
    )


def build_graph(phases: list[RoadmapPhase]) -> DependencyGraph:
    """Build graph from phases, using explicit deps when available."""
    all_nodes = [node for phase in phases for node in phase.nodes]
    has_explicit_deps = any(node.depends_on is not None for node in all_nodes)
    if has_explicit_deps:
        return graph_from_nodes(all_nodes)
    return graph_from_phases(phases)


def nodes_from_graph(graph: DependencyGraph) -> list[RoadmapNode]:
    """Convert graph nodes to flat RoadmapNode list (inverse of graph_from_phases).

    Preserves dependency information so it can be serialized to YAML frontmatter
    via render_roadmap_block_inner().
    """
    return [
        RoadmapNode(
            id=node.id,
            description=node.description,
            status=node.status,
            plan=node.plan,
            pr=node.pr,
            depends_on=node.depends_on,
        )
        for node in graph.nodes
    ]


def phases_from_graph(graph: DependencyGraph) -> list[RoadmapPhase]:
    """Convert graph back to phases (inverse of graph_from_phases).

    Phase names are placeholders — use enrich_phase_names() to restore from body text.
    """
    return group_nodes_by_phase(nodes_from_graph(graph))


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


def build_state_sparkline(nodes: tuple[ObjectiveNode, ...]) -> str:
    """Build a compact sparkline showing each node's status in position order.

    Symbols: ✓ done, ▶ active (in_progress/planning), ○ pending, ⊘ blocked, - skipped.

    Args:
        nodes: Objective nodes in graph order

    Returns:
        Sparkline string like "✓✓✓▶▶○○○○"
    """
    return "".join(_STATUS_SYMBOLS.get(node.status, "?") for node in nodes)


def _find_node_by_status(
    nodes: tuple[ObjectiveNode, ...], status: RoadmapNodeStatus
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
        (phase.name for phase in phases if any(n.id == target_node.id for n in phase.nodes)),
        "",
    )

    return {
        "id": target_node.id,
        "description": target_node.description,
        "phase": phase_name,
    }


def parse_graph(body: str) -> tuple[DependencyGraph, list[RoadmapPhase], list[str]] | None:
    """Parse a v2 roadmap body into both graph and phases.

    Convenience function combining parse_v2_roadmap + graph_from_phases/graph_from_nodes.
    Most callers need both graph (for logic) and phases (for display grouping).

    When any node has explicit depends_on, uses graph_from_nodes() for the graph.
    Otherwise falls back to graph_from_phases() which infers sequential dependencies.

    Args:
        body: Full objective body text with metadata blocks and markdown headers.

    Returns:
        (graph, enriched_phases, errors) or None if body is not v2 format.
    """
    v2_result = parse_v2_roadmap(body)
    if v2_result is None:
        return None
    phases, errors = v2_result
    graph = build_graph(phases)
    return (graph, phases, errors)
