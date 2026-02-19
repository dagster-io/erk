"""Unit tests for ObjectiveNode, DependencyGraph, graph_from_phases(), and round-trip."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    build_graph,
    compute_graph_summary,
    find_graph_next_node,
    graph_from_nodes,
    graph_from_phases,
    nodes_from_graph,
    parse_graph,
    phases_from_graph,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapNode,
    RoadmapPhase,
    compute_summary,
    find_next_node,
    render_roadmap_block_inner,
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
) -> RoadmapNode:
    return RoadmapNode(
        id=id,
        description=f"Step {id}",
        status=status,  # type: ignore[arg-type]
        plan=plan,
        pr=pr,
        depends_on=None,
    )


def _step_with_deps(
    *,
    id: str,
    status: str,
    depends_on: tuple[str, ...],
) -> RoadmapNode:
    return RoadmapNode(
        id=id,
        description=f"Step {id}",
        status=status,  # type: ignore[arg-type]
        plan=None,
        pr=None,
        depends_on=depends_on,
    )


def _phase(*, number: int, nodes: list[RoadmapNode]) -> RoadmapPhase:
    return RoadmapPhase(
        number=number,
        suffix="",
        name=f"Phase {number}",
        nodes=nodes,
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

    def test_pending_unblocked_nodes_fan_out(self) -> None:
        """pending_unblocked_nodes returns multiple pending nodes when fan-out allows it."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="2.1", status="pending", depends_on=("1.1",)),
                _node(id="2.2", status="pending", depends_on=("1.1",)),
            )
        )
        result = graph.pending_unblocked_nodes()
        assert [n.id for n in result] == ["2.1", "2.2"]

    def test_pending_unblocked_nodes_excludes_non_pending(self) -> None:
        """pending_unblocked_nodes excludes done/in_progress/skipped nodes."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="in_progress", depends_on=()),
                _node(id="1.3", status="skipped", depends_on=()),
                _node(id="1.4", status="pending", depends_on=()),
            )
        )
        result = graph.pending_unblocked_nodes()
        assert [n.id for n in result] == ["1.4"]

    def test_pending_unblocked_nodes_all_done(self) -> None:
        """pending_unblocked_nodes returns empty list when all nodes are done."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="done", depends_on=("1.1",)),
            )
        )
        assert graph.pending_unblocked_nodes() == []

    def test_pending_unblocked_nodes_blocked(self) -> None:
        """pending_unblocked_nodes returns empty list when pending nodes are blocked."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="pending", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
            )
        )
        # 1.1 is unblocked+pending, 1.2 is blocked by 1.1
        result = graph.pending_unblocked_nodes()
        assert [n.id for n in result] == ["1.1"]

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
# min_dep_status() tests
# ---------------------------------------------------------------------------


class TestMinDepStatus:
    def test_no_deps_returns_none(self) -> None:
        graph = DependencyGraph(nodes=(_node(id="1.1", status="pending", depends_on=()),))
        assert graph.min_dep_status("1.1") is None

    def test_all_deps_done_returns_done(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="done", depends_on=()),
                _node(id="2.1", status="pending", depends_on=("1.1", "1.2")),
            )
        )
        assert graph.min_dep_status("2.1") == "done"

    def test_mixed_statuses_returns_lowest(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="pending", depends_on=()),
                _node(id="1.2", status="done", depends_on=()),
                _node(id="2.1", status="pending", depends_on=("1.1", "1.2")),
            )
        )
        assert graph.min_dep_status("2.1") == "pending"

    def test_all_statuses_returns_pending(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="pending", depends_on=()),
                _node(id="1.2", status="blocked", depends_on=()),
                _node(id="1.3", status="planning", depends_on=()),
                _node(id="1.4", status="in_progress", depends_on=()),
                _node(id="1.5", status="done", depends_on=()),
                _node(id="2.1", status="pending", depends_on=("1.1", "1.2", "1.3", "1.4", "1.5")),
            )
        )
        assert graph.min_dep_status("2.1") == "pending"

    def test_unknown_node_id_returns_none(self) -> None:
        graph = DependencyGraph(nodes=(_node(id="1.1", status="done", depends_on=()),))
        assert graph.min_dep_status("nonexistent") is None


# ---------------------------------------------------------------------------
# graph_from_phases() conversion
# ---------------------------------------------------------------------------


class TestGraphFromPhases:
    def test_single_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                nodes=[
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
                nodes=[
                    _step(id="1.1", status="pending", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
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
                nodes=[
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
# Equivalence with find_next_node()
# ---------------------------------------------------------------------------


class TestEquivalenceWithFindNextNode:
    """Verify graph.next_node() matches find_next_node() for sequential phases."""

    @staticmethod
    def _assert_equivalent(phases: list[RoadmapPhase]) -> None:
        legacy_result = find_next_node(phases)
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
                nodes=[
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
                nodes=[
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
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
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
                nodes=[
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
                nodes=[
                    _step(id="1.1", status="skipped", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            )
        ]
        self._assert_equivalent(phases)


# ---------------------------------------------------------------------------
# nodes_from_graph() tests
# ---------------------------------------------------------------------------


class TestStepsFromGraph:
    def test_preserves_fields(self) -> None:
        graph = DependencyGraph(
            nodes=(
                ObjectiveNode(
                    id="1.1",
                    description="Setup infra",
                    status="done",
                    plan="#100",
                    pr="#200",
                    depends_on=(),
                ),
            )
        )
        steps = nodes_from_graph(graph)

        assert len(steps) == 1
        assert steps[0].id == "1.1"
        assert steps[0].description == "Setup infra"
        assert steps[0].status == "done"
        assert steps[0].plan == "#100"
        assert steps[0].pr == "#200"

    def test_ordering_matches_node_order(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="2.1", status="pending", depends_on=()),
                _node(id="1.1", status="done", depends_on=()),
                _node(id="3.1", status="pending", depends_on=()),
            )
        )
        steps = nodes_from_graph(graph)

        assert [s.id for s in steps] == ["2.1", "1.1", "3.1"]

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes=())
        steps = nodes_from_graph(graph)

        assert steps == []

    def test_preserves_depends_on(self) -> None:
        """nodes_from_graph preserves depends_on from ObjectiveNode to RoadmapNode."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
            )
        )
        steps = nodes_from_graph(graph)

        assert len(steps) == 2
        assert steps[0].depends_on == ()
        assert steps[1].depends_on == ("1.1",)


# ---------------------------------------------------------------------------
# phases_from_graph() tests
# ---------------------------------------------------------------------------


class TestPhasesFromGraph:
    def test_single_phase(self) -> None:
        graph = graph_from_phases(
            [
                _phase(
                    number=1,
                    nodes=[
                        _step(id="1.1", status="pending", plan=None, pr=None),
                        _step(id="1.2", status="done", plan=None, pr=None),
                    ],
                )
            ]
        )
        phases = phases_from_graph(graph)

        assert len(phases) == 1
        assert phases[0].number == 1
        assert len(phases[0].nodes) == 2

    def test_multi_phase(self) -> None:
        graph = graph_from_phases(
            [
                _phase(
                    number=1,
                    nodes=[_step(id="1.1", status="pending", plan=None, pr=None)],
                ),
                _phase(
                    number=2,
                    nodes=[_step(id="2.1", status="pending", plan=None, pr=None)],
                ),
            ]
        )
        phases = phases_from_graph(graph)

        assert len(phases) == 2
        assert phases[0].number == 1
        assert phases[1].number == 2

    def test_sub_phases(self) -> None:
        phases_in = [
            RoadmapPhase(
                number=1,
                suffix="A",
                name="Phase 1A",
                nodes=[_step(id="1A.1", status="pending", plan=None, pr=None)],
            ),
            RoadmapPhase(
                number=1,
                suffix="B",
                name="Phase 1B",
                nodes=[_step(id="1B.1", status="pending", plan=None, pr=None)],
            ),
        ]
        graph = graph_from_phases(phases_in)
        phases_out = phases_from_graph(graph)

        assert len(phases_out) == 2
        assert phases_out[0].number == 1
        assert phases_out[0].suffix == "A"
        assert phases_out[1].number == 1
        assert phases_out[1].suffix == "B"

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes=())
        phases = phases_from_graph(graph)

        assert phases == []


# ---------------------------------------------------------------------------
# Round-trip tests: phases → graph → phases preserves step data
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @staticmethod
    def _assert_steps_equivalent(
        original: list[RoadmapPhase], recovered: list[RoadmapPhase]
    ) -> None:
        """Assert that step data (id, description, status, plan, pr) matches across phases."""
        original_steps = [s for p in original for s in p.nodes]
        recovered_steps = [s for p in recovered for s in p.nodes]
        assert len(original_steps) == len(recovered_steps)
        for orig, rec in zip(original_steps, recovered_steps, strict=True):
            assert orig.id == rec.id
            assert orig.description == rec.description
            assert orig.status == rec.status
            assert orig.plan == rec.plan
            assert orig.pr == rec.pr

    def test_single_phase(self) -> None:
        original = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="pending", plan=None, pr=None),
                    _step(id="1.2", status="done", plan="#10", pr="#20"),
                ],
            )
        ]
        recovered = phases_from_graph(graph_from_phases(original))

        self._assert_steps_equivalent(original, recovered)

    def test_multi_phase(self) -> None:
        original = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr="#1"),
                    _step(id="1.2", status="in_progress", plan="#50", pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step(id="2.1", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        recovered = phases_from_graph(graph_from_phases(original))

        self._assert_steps_equivalent(original, recovered)

    def test_sub_phases(self) -> None:
        original = [
            RoadmapPhase(
                number=1,
                suffix="A",
                name="Phase 1A",
                nodes=[_step(id="1A.1", status="done", plan=None, pr="#5")],
            ),
            RoadmapPhase(
                number=1,
                suffix="B",
                name="Phase 1B",
                nodes=[_step(id="1B.1", status="pending", plan=None, pr=None)],
            ),
        ]
        recovered = phases_from_graph(graph_from_phases(original))

        self._assert_steps_equivalent(original, recovered)
        assert recovered[0].suffix == "A"
        assert recovered[1].suffix == "B"

    def test_mixed_statuses_with_plan_pr(self) -> None:
        original = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan="#10", pr="#20"),
                    _step(id="1.2", status="in_progress", plan="#30", pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                    _step(id="1.4", status="blocked", plan=None, pr=None),
                    _step(id="1.5", status="skipped", plan=None, pr=None),
                ],
            )
        ]
        recovered = phases_from_graph(graph_from_phases(original))

        self._assert_steps_equivalent(original, recovered)


# ---------------------------------------------------------------------------
# compute_graph_summary() tests
# ---------------------------------------------------------------------------


class TestComputeGraphSummary:
    def test_mixed_statuses(self) -> None:
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="in_progress", depends_on=("1.1",)),
                _node(id="1.3", status="pending", depends_on=("1.2",)),
                _node(id="1.4", status="blocked", depends_on=()),
                _node(id="1.5", status="skipped", depends_on=()),
                _node(id="1.6", status="planning", depends_on=()),
            )
        )
        summary = compute_graph_summary(graph)

        assert summary["total_nodes"] == 6
        assert summary["done"] == 1
        assert summary["in_progress"] == 1
        assert summary["pending"] == 1
        assert summary["blocked"] == 1
        assert summary["skipped"] == 1
        assert summary["planning"] == 1

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes=())
        summary = compute_graph_summary(graph)

        assert summary["total_nodes"] == 0
        assert summary["done"] == 0
        assert summary["pending"] == 0

    def test_matches_compute_summary_from_phases(self) -> None:
        """Verify graph summary matches phase-based summary."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan="#10", pr="#20"),
                    _step(id="1.2", status="in_progress", plan="#30", pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step(id="2.1", status="blocked", plan=None, pr=None),
                    _step(id="2.2", status="skipped", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)

        assert compute_graph_summary(graph) == compute_summary(phases)


# ---------------------------------------------------------------------------
# find_graph_next_node() tests
# ---------------------------------------------------------------------------


class TestFindGraphNextNode:
    def test_returns_next_pending_with_phase(self) -> None:
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        result = find_graph_next_node(graph, phases)

        assert result is not None
        assert result["id"] == "1.2"
        assert result["description"] == "Step 1.2"
        assert result["phase"] == "Phase 1"

    def test_returns_none_all_done(self) -> None:
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        result = find_graph_next_node(graph, phases)

        assert result is None

    def test_cross_phase_next(self) -> None:
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step(id="2.1", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        result = find_graph_next_node(graph, phases)

        assert result is not None
        assert result["id"] == "2.1"
        assert result["phase"] == "Phase 2"

    def test_falls_back_to_in_progress_when_no_pending(self) -> None:
        """When all remaining steps are in_progress, returns the first one."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step(id="2.1", status="in_progress", plan=None, pr=None),
                    _step(id="2.2", status="in_progress", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        result = find_graph_next_node(graph, phases)

        assert result is not None
        assert result["id"] == "2.1"
        assert result["description"] == "Step 2.1"
        assert result["phase"] == "Phase 2"

    def test_matches_find_next_node(self) -> None:
        """Verify graph next step matches phase-based next step."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="in_progress", plan=None, pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        graph = graph_from_phases(phases)
        graph_result = find_graph_next_node(graph, phases)
        legacy_result = find_next_node(phases)

        assert graph_result is not None
        assert legacy_result is not None
        assert graph_result["id"] == legacy_result["id"]
        assert graph_result["phase"] == legacy_result["phase"]


# ---------------------------------------------------------------------------
# parse_graph() tests
# ---------------------------------------------------------------------------


_V2_BODY = """\
# Objective

### Phase 1: Foundation

### Phase 2: Build

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: '#100'
- id: '2.1'
  description: Build core
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


class TestParseGraph:
    def test_parses_v2_body(self) -> None:
        result = parse_graph(_V2_BODY)

        assert result is not None
        graph, phases, errors = result
        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == "1.1"
        assert graph.nodes[0].status == "done"
        assert graph.nodes[1].id == "2.1"
        assert graph.nodes[1].status == "pending"
        assert len(phases) == 2
        assert phases[0].name == "Foundation"
        assert phases[1].name == "Build"
        assert errors == []

    def test_returns_none_for_non_v2(self) -> None:
        result = parse_graph("Just some text with no roadmap")

        assert result is None

    def test_graph_and_phases_are_consistent(self) -> None:
        result = parse_graph(_V2_BODY)

        assert result is not None
        graph, phases, _errors = result
        # Graph nodes should match flattened phase nodes
        phase_node_ids = [n.id for phase in phases for n in phase.nodes]
        graph_node_ids = [node.id for node in graph.nodes]
        assert graph_node_ids == phase_node_ids

    def test_uses_explicit_deps_when_present(self) -> None:
        """parse_graph uses graph_from_nodes when nodes have explicit depends_on."""
        body = """\
# Objective

### Phase 1: Foundation

### Phase 2: Build

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '3'
nodes:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: '#100'
  depends_on: []
- id: '2.1'
  description: Build core
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
        result = parse_graph(body)

        assert result is not None
        graph, phases, errors = result
        assert errors == []
        assert len(graph.nodes) == 2
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)
        assert len(phases) == 2

    def test_falls_back_to_inferred_deps(self) -> None:
        """parse_graph uses graph_from_phases when no node has explicit depends_on."""
        result = parse_graph(_V2_BODY)

        assert result is not None
        graph, _phases, _errors = result
        # graph_from_phases infers sequential deps
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)


# ---------------------------------------------------------------------------
# graph_from_nodes() tests
# ---------------------------------------------------------------------------


class TestGraphFromNodes:
    def test_explicit_deps(self) -> None:
        """graph_from_nodes uses explicit depends_on from RoadmapNode."""
        nodes = [
            RoadmapNode(
                id="1.1", description="A", status="done", plan=None, pr=None, depends_on=()
            ),
            RoadmapNode(
                id="1.2",
                description="B",
                status="pending",
                plan=None,
                pr=None,
                depends_on=("1.1",),
            ),
        ]
        graph = graph_from_nodes(nodes)

        assert len(graph.nodes) == 2
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)

    def test_fan_out(self) -> None:
        """Two nodes depend on the same parent (fan-out)."""
        nodes = [
            RoadmapNode(
                id="1.1", description="Root", status="done", plan=None, pr=None, depends_on=()
            ),
            RoadmapNode(
                id="2.1",
                description="Branch A",
                status="pending",
                plan=None,
                pr=None,
                depends_on=("1.1",),
            ),
            RoadmapNode(
                id="2.2",
                description="Branch B",
                status="pending",
                plan=None,
                pr=None,
                depends_on=("1.1",),
            ),
        ]
        graph = graph_from_nodes(nodes)

        assert len(graph.nodes) == 3
        assert graph.nodes[1].depends_on == ("1.1",)
        assert graph.nodes[2].depends_on == ("1.1",)

    def test_fan_in(self) -> None:
        """One node depends on two parents (fan-in)."""
        nodes = [
            RoadmapNode(
                id="1.1", description="A", status="done", plan=None, pr=None, depends_on=()
            ),
            RoadmapNode(
                id="2.1", description="B", status="done", plan=None, pr=None, depends_on=()
            ),
            RoadmapNode(
                id="3.1",
                description="Merge",
                status="pending",
                plan=None,
                pr=None,
                depends_on=("1.1", "2.1"),
            ),
        ]
        graph = graph_from_nodes(nodes)

        assert len(graph.nodes) == 3
        assert graph.nodes[2].depends_on == ("1.1", "2.1")

    def test_none_depends_on_treated_as_no_deps(self) -> None:
        """Nodes with depends_on=None are treated as having no dependencies."""
        nodes = [
            RoadmapNode(
                id="1.1", description="A", status="pending", plan=None, pr=None, depends_on=None
            ),
        ]
        graph = graph_from_nodes(nodes)

        assert graph.nodes[0].depends_on == ()


# ---------------------------------------------------------------------------
# build_graph() tests
# ---------------------------------------------------------------------------


class TestBuildGraph:
    def test_uses_explicit_deps_when_present(self) -> None:
        """Fan-out nodes with explicit deps — both children unblocked simultaneously."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step_with_deps(id="1.1", status="done", depends_on=()),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step_with_deps(id="2.1", status="pending", depends_on=("1.1",)),
                    _step_with_deps(id="2.2", status="pending", depends_on=("1.1",)),
                ],
            ),
        ]
        graph = build_graph(phases)

        # Both 2.1 and 2.2 depend only on 1.1 (fan-out), not sequentially
        assert graph.nodes[1].depends_on == ("1.1",)
        assert graph.nodes[2].depends_on == ("1.1",)
        unblocked_ids = [n.id for n in graph.unblocked_nodes() if n.status == "pending"]
        assert unblocked_ids == ["2.1", "2.2"]

    def test_falls_back_to_inferred_deps(self) -> None:
        """Nodes with depends_on=None — verify sequential inference."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        graph = build_graph(phases)

        # Sequential: 1.2 depends on 1.1
        assert graph.nodes[0].depends_on == ()
        assert graph.nodes[1].depends_on == ("1.1",)

    def test_fan_out_unblocked_simultaneously(self) -> None:
        """1 parent (done) + 2 children → both children unblocked."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step_with_deps(id="1.1", status="done", depends_on=()),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step_with_deps(id="2.1", status="pending", depends_on=("1.1",)),
                    _step_with_deps(id="2.2", status="pending", depends_on=("1.1",)),
                ],
            ),
        ]
        graph = build_graph(phases)

        unblocked = graph.unblocked_nodes()
        unblocked_pending = [n for n in unblocked if n.status == "pending"]
        assert len(unblocked_pending) == 2
        assert {n.id for n in unblocked_pending} == {"2.1", "2.2"}

    def test_fan_in_blocked_until_all_parents_done(self) -> None:
        """2 parents (1 done, 1 pending) + 1 merge → merge blocked."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step_with_deps(id="1.1", status="done", depends_on=()),
                    _step_with_deps(id="1.2", status="pending", depends_on=()),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step_with_deps(id="2.1", status="pending", depends_on=("1.1", "1.2")),
                ],
            ),
        ]
        graph = build_graph(phases)

        unblocked_ids = {n.id for n in graph.unblocked_nodes()}
        # 2.1 should NOT be unblocked because 1.2 is still pending
        assert "2.1" not in unblocked_ids

    def test_fan_in_unblocked_when_all_parents_done(self) -> None:
        """2 parents (both done) + 1 merge → merge unblocked."""
        phases = [
            _phase(
                number=1,
                nodes=[
                    _step_with_deps(id="1.1", status="done", depends_on=()),
                    _step_with_deps(id="1.2", status="done", depends_on=()),
                ],
            ),
            _phase(
                number=2,
                nodes=[
                    _step_with_deps(id="2.1", status="pending", depends_on=("1.1", "1.2")),
                ],
            ),
        ]
        graph = build_graph(phases)

        unblocked_ids = {n.id for n in graph.unblocked_nodes()}
        assert "2.1" in unblocked_ids

    def test_empty_phases(self) -> None:
        """Empty input returns empty graph."""
        graph = build_graph([])

        assert graph.nodes == ()


# ---------------------------------------------------------------------------
# Fan-out/fan-in round-trip test
# ---------------------------------------------------------------------------


def test_fan_out_fan_in_round_trip() -> None:
    """Create nodes with fan-out + fan-in → render to YAML → parse back → verify."""
    nodes = [
        RoadmapNode(
            id="1.1", description="Root", status="done", plan=None, pr="#100", depends_on=()
        ),
        RoadmapNode(
            id="2.1",
            description="Branch A",
            status="pending",
            plan=None,
            pr=None,
            depends_on=("1.1",),
        ),
        RoadmapNode(
            id="2.2",
            description="Branch B",
            status="pending",
            plan=None,
            pr=None,
            depends_on=("1.1",),
        ),
        RoadmapNode(
            id="3.1",
            description="Merge",
            status="pending",
            plan=None,
            pr=None,
            depends_on=("2.1", "2.2"),
        ),
    ]

    # Render to YAML via render_roadmap_block_inner
    yaml_content = render_roadmap_block_inner(nodes)

    # Wrap in metadata block markers for parse_graph
    body = (
        "# Objective\n\n"
        "### Phase 1: Root\n\n"
        "### Phase 2: Branches\n\n"
        "### Phase 3: Merge\n\n"
        f"<!-- erk:metadata-block:objective-roadmap -->\n"
        f"{yaml_content}\n"
        f"<!-- /erk:metadata-block:objective-roadmap -->\n"
    )

    result = parse_graph(body)
    assert result is not None
    graph, phases, errors = result

    assert errors == []
    assert len(graph.nodes) == 4

    # Verify depends_on preserved
    node_map = {n.id: n for n in graph.nodes}
    assert node_map["1.1"].depends_on == ()
    assert node_map["2.1"].depends_on == ("1.1",)
    assert node_map["2.2"].depends_on == ("1.1",)
    assert node_map["3.1"].depends_on == ("2.1", "2.2")

    # Verify unblocked nodes: 1.1 is done, so 2.1 and 2.2 are unblocked
    unblocked_pending = [n for n in graph.unblocked_nodes() if n.status == "pending"]
    assert {n.id for n in unblocked_pending} == {"2.1", "2.2"}
