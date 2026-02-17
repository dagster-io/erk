"""Unit tests for ObjectiveNode, DependencyGraph, and graph_from_phases()."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    graph_from_phases,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    RoadmapStep,
    find_next_step,
)


def _node(
    *,
    id: str,
    status: str,
    depends_on: tuple[str, ...],
) -> ObjectiveNode:
    return ObjectiveNode(
        id=id,
        description=f"Step {id}",
        status=status,  # type: ignore[arg-type]
        plan=None,
        pr=None,
        depends_on=depends_on,
    )


def _step(
    *,
    id: str,
    status: str,
    plan: str | None,
    pr: str | None,
) -> RoadmapStep:
    return RoadmapStep(
        id=id,
        description=f"Step {id}",
        status=status,  # type: ignore[arg-type]
        plan=plan,
        pr=pr,
    )


def _phase(*, number: int, steps: list[RoadmapStep]) -> RoadmapPhase:
    return RoadmapPhase(
        number=number,
        suffix="",
        name=f"Phase {number}",
        steps=steps,
    )


# ---------------------------------------------------------------------------
# ObjectiveNode and DependencyGraph basics
# ---------------------------------------------------------------------------


class TestDependencyGraphBasics:
    def test_unblocked_nodes_all_pending_no_deps(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="pending", depends_on=()),
                _node(id="1.2", status="pending", depends_on=()),
            )
        )
        unblocked = graph.unblocked_nodes()
        assert [n.id for n in unblocked] == ["1.1", "1.2"]

    def test_unblocked_nodes_with_deps(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="pending", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
            )
        )
        unblocked = graph.unblocked_nodes()
        assert [n.id for n in unblocked] == ["1.1"]

    def test_unblocked_nodes_skipped_satisfies_dep(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="skipped", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
            )
        )
        unblocked = graph.unblocked_nodes()
        assert [n.id for n in unblocked] == ["1.1", "1.2"]

    def test_next_node_returns_first_unblocked_pending(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
                _node(id="1.3", status="pending", depends_on=("1.2",)),
            )
        )
        result = graph.next_node()
        assert result is not None
        assert result.id == "1.2"

    def test_next_node_returns_none_all_done(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="done", depends_on=("1.1",)),
            )
        )
        assert graph.next_node() is None

    def test_next_node_skips_non_pending_statuses(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="in_progress", depends_on=()),
                _node(id="1.2", status="blocked", depends_on=()),
                _node(id="1.3", status="planning", depends_on=()),
                _node(id="1.4", status="pending", depends_on=()),
            )
        )
        result = graph.next_node()
        assert result is not None
        assert result.id == "1.4"

    def test_is_complete_all_done(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="done", depends_on=()),
            )
        )
        assert graph.is_complete() is True

    def test_is_complete_has_pending(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="pending", depends_on=()),
            )
        )
        assert graph.is_complete() is False

    def test_is_complete_mixed_done_and_skipped(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="skipped", depends_on=()),
            )
        )
        assert graph.is_complete() is True


# ---------------------------------------------------------------------------
# graph_from_phases() conversion
# ---------------------------------------------------------------------------


class TestGraphFromPhases:
    def test_single_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="pending", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            )
        ]
        graph = graph_from_phases(phases)
        assert len(graph.nodes) == 3
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)
        assert graph.nodes[2].depends_on == ("1.2",)

    def test_multi_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="pending", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
                    _step(id="2.1", status="pending", plan=None, pr=None),
                    _step(id="2.2", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        assert len(graph.nodes) == 4
        # Phase 1 internal deps
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)
        # Cross-phase: 2.1 depends on 1.2 (last step of prev phase)
        assert graph.nodes[2].depends_on == ("1.2",)
        assert graph.nodes[3].depends_on == ("2.1",)

    def test_empty(self) -> None:
        graph = graph_from_phases([])
        assert graph.nodes == ()

    def test_preserves_fields(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="done", plan="#100", pr="#200"),
                ],
            )
        ]
        graph = graph_from_phases(phases)
        node = graph.nodes[0]
        assert node.id == "1.1"
        assert node.status == "done"
        assert node.plan == "#100"
        assert node.pr == "#200"
        assert node.description == "Step 1.1"


# ---------------------------------------------------------------------------
# Equivalence with find_next_step()
# ---------------------------------------------------------------------------


class TestEquivalenceWithFindNextStep:
    """Verify graph.next_node() matches find_next_step() for sequential phases."""

    @staticmethod
    def _assert_equivalent(phases: list[RoadmapPhase]) -> None:
        legacy_result = find_next_step(phases)
        graph_result = graph_from_phases(phases).next_node()

        if legacy_result is None:
            assert graph_result is None
        else:
            assert graph_result is not None
            assert graph_result.id == legacy_result["id"]

    def test_basic(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="pending", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                ],
            )
        ]
        self._assert_equivalent(phases)

    def test_mid_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            )
        ]
        self._assert_equivalent(phases)

    def test_cross_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
                    _step(id="2.1", status="pending", plan=None, pr=None),
                    _step(id="2.2", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        self._assert_equivalent(phases)

    def test_all_done(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            )
        ]
        self._assert_equivalent(phases)

    def test_with_skipped(self) -> None:
        phases = [
            _phase(
                number=1,
                steps=[
                    _step(id="1.1", status="skipped", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            )
        ]
        self._assert_equivalent(phases)
