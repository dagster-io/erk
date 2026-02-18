"""Unit tests for ObjectiveNode, DependencyGraph, graph_from_phases(), and round-trip."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    compute_graph_summary,
    find_graph_next_node,
    graph_from_phases,
    parse_graph,
    phases_from_graph,
    steps_from_graph,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    RoadmapStep,
    compute_summary,
    find_next_node,
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


# ---------------------------------------------------------------------------
# steps_from_graph() tests
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
        steps = steps_from_graph(graph)

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
        steps = steps_from_graph(graph)

        assert [s.id for s in steps] == ["2.1", "1.1", "3.1"]

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes=())
        steps = steps_from_graph(graph)

        assert steps == []

    def test_strips_depends_on(self) -> None:
        """steps_from_graph returns RoadmapStep which has no depends_on field."""
        graph = DependencyGraph(
            nodes=(
                _node(id="1.1", status="done", depends_on=()),
                _node(id="1.2", status="pending", depends_on=("1.1",)),
            )
        )
        steps = steps_from_graph(graph)

        assert len(steps) == 2
        assert not hasattr(steps[0], "depends_on")


# ---------------------------------------------------------------------------
# phases_from_graph() tests
# ---------------------------------------------------------------------------


class TestPhasesFromGraph:
    def test_single_phase(self) -> None:
        graph = graph_from_phases(
            [
                _phase(
                    number=1,
                    steps=[
                        _step(id="1.1", status="pending", plan=None, pr=None),
                        _step(id="1.2", status="done", plan=None, pr=None),
                    ],
                )
            ]
        )
        phases = phases_from_graph(graph)

        assert len(phases) == 1
        assert phases[0].number == 1
        assert len(phases[0].steps) == 2

    def test_multi_phase(self) -> None:
        graph = graph_from_phases(
            [
                _phase(
                    number=1,
                    steps=[_step(id="1.1", status="pending", plan=None, pr=None)],
                ),
                _phase(
                    number=2,
                    steps=[_step(id="2.1", status="pending", plan=None, pr=None)],
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
                steps=[_step(id="1A.1", status="pending", plan=None, pr=None)],
            ),
            RoadmapPhase(
                number=1,
                suffix="B",
                name="Phase 1B",
                steps=[_step(id="1B.1", status="pending", plan=None, pr=None)],
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
        original_steps = [s for p in original for s in p.steps]
        recovered_steps = [s for p in recovered for s in p.steps]
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
                steps=[
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
                steps=[
                    _step(id="1.1", status="done", plan=None, pr="#1"),
                    _step(id="1.2", status="in_progress", plan="#50", pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
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
                steps=[_step(id="1A.1", status="done", plan=None, pr="#5")],
            ),
            RoadmapPhase(
                number=1,
                suffix="B",
                name="Phase 1B",
                steps=[_step(id="1B.1", status="pending", plan=None, pr=None)],
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
                steps=[
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
                steps=[
                    _step(id="1.1", status="done", plan="#10", pr="#20"),
                    _step(id="1.2", status="in_progress", plan="#30", pr=None),
                    _step(id="1.3", status="pending", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
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
                steps=[
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
                steps=[
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
                steps=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
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
                steps=[
                    _step(id="1.1", status="done", plan=None, pr=None),
                    _step(id="1.2", status="done", plan=None, pr=None),
                ],
            ),
            _phase(
                number=2,
                steps=[
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
                steps=[
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
        # Graph nodes should match flattened phase steps
        phase_step_ids = [step.id for phase in phases for step in phase.steps]
        graph_node_ids = [node.id for node in graph.nodes]
        assert graph_node_ids == phase_step_ids
