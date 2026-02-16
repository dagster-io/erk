"""Dependency graph representation for objective roadmaps.

Provides ObjectiveNode and DependencyGraph types that model step dependencies
explicitly, plus a graph_from_phases() parser that infers sequential dependencies
from existing RoadmapPhase/RoadmapStep data.

Phase 1 of Objective #7242: these types coexist alongside the existing
RoadmapStep/RoadmapPhase types. Phase 2 will migrate callers.
"""

from dataclasses import dataclass

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    RoadmapStepStatus,
)


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
        satisfied_statuses: set[RoadmapStepStatus] = {"done", "skipped"}
        result: list[ObjectiveNode] = []
        for node in self.nodes:
            all_satisfied = all(
                node_map[dep_id].status in satisfied_statuses
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
        return all(node.status in {"done", "skipped"} for node in self.nodes)


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
