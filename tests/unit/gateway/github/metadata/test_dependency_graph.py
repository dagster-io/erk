"""Unit tests for dependency_graph sparkline, find_graph_next_node, and head state."""

import pytest

from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    build_state_sparkline,
    compute_objective_head_state,
    find_graph_next_node,
    phases_from_graph,
)


def _make_node(
    node_id: str,
    *,
    status: str = "pending",
    depends_on: tuple[str, ...] = (),
) -> ObjectiveNode:
    return ObjectiveNode(
        id=node_id,
        description=f"Node {node_id}",
        status=status,
        pr=None,
        depends_on=depends_on,
        slug=None,
    )


# ---------------------------------------------------------------------------
# Sparkline symbol tests
# ---------------------------------------------------------------------------


def test_sparkline_planning_renders_as_half_circle() -> None:
    """Planning nodes render as ◐ (distinct from ▶ for in_progress)."""
    nodes = (
        _make_node("1.1", status="done"),
        _make_node("1.2", status="planning"),
        _make_node("1.3", status="pending"),
    )
    result = build_state_sparkline(nodes)
    assert result == "✓◐○"


def test_sparkline_in_progress_renders_as_triangle() -> None:
    """In-progress nodes still render as ▶."""
    nodes = (
        _make_node("1.1", status="done"),
        _make_node("1.2", status="in_progress"),
    )
    result = build_state_sparkline(nodes)
    assert result == "✓▶"


def test_sparkline_planning_and_in_progress_distinct() -> None:
    """Planning (◐) and in_progress (▶) have distinct symbols."""
    nodes = (
        _make_node("1.1", status="planning"),
        _make_node("1.2", status="in_progress"),
    )
    result = build_state_sparkline(nodes)
    assert result == "◐▶"


# ---------------------------------------------------------------------------
# find_graph_next_node fallback order tests
# ---------------------------------------------------------------------------


def test_find_graph_next_node_prefers_pending() -> None:
    """Pending nodes are preferred over planning and in_progress."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="pending"),
            _make_node("1.3", status="planning"),
            _make_node("1.4", status="in_progress"),
        )
    )
    phases = phases_from_graph(graph)
    result = find_graph_next_node(graph, phases)
    assert result is not None
    assert result["id"] == "1.2"
    assert result["status"] == "pending"


def test_find_graph_next_node_falls_back_to_planning() -> None:
    """When no pending nodes, planning is tried before in_progress."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="planning"),
            _make_node("1.3", status="in_progress"),
        )
    )
    phases = phases_from_graph(graph)
    result = find_graph_next_node(graph, phases)
    assert result is not None
    assert result["id"] == "1.2"
    assert result["status"] == "planning"


def test_find_graph_next_node_falls_back_to_in_progress() -> None:
    """When no pending or planning nodes, falls back to in_progress."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="in_progress"),
        )
    )
    phases = phases_from_graph(graph)
    result = find_graph_next_node(graph, phases)
    assert result is not None
    assert result["id"] == "1.2"
    assert result["status"] == "in_progress"


def test_find_graph_next_node_returns_none_when_all_done() -> None:
    """Returns None when all nodes are in terminal status."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="skipped"),
        )
    )
    phases = phases_from_graph(graph)
    result = find_graph_next_node(graph, phases)
    assert result is None


def test_find_graph_next_node_includes_status_key() -> None:
    """Returned dict includes the 'status' key."""
    graph = DependencyGraph(nodes=(_make_node("1.1", status="pending"),))
    phases = phases_from_graph(graph)
    result = find_graph_next_node(graph, phases)
    assert result is not None
    assert "status" in result
    assert result["status"] == "pending"


# ---------------------------------------------------------------------------
# min_dep_status tests
# ---------------------------------------------------------------------------


def test_min_dep_status_returns_none_for_no_deps() -> None:
    """Node with no depends_on returns None."""
    graph = DependencyGraph(nodes=(_make_node("1.1", status="pending"),))
    assert graph.min_dep_status("1.1") is None


def test_min_dep_status_returns_lowest_status() -> None:
    """Node depending on nodes with mixed statuses returns the lowest."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="planning"),
            _make_node("1.3", status="pending", depends_on=("1.1", "1.2")),
        )
    )
    # "planning" (order 2) < "done" (order 4), so min is "planning"
    assert graph.min_dep_status("1.3") == "planning"


def test_min_dep_status_returns_terminal_when_all_deps_done() -> None:
    """Returns 'done' when all deps are done/skipped."""
    graph = DependencyGraph(
        nodes=(
            _make_node("1.1", status="done"),
            _make_node("1.2", status="skipped"),
            _make_node("1.3", status="pending", depends_on=("1.1", "1.2")),
        )
    )
    # "done" (order 4) < "skipped" (order 5), so min is "done"
    assert graph.min_dep_status("1.3") == "done"


# ---------------------------------------------------------------------------
# compute_objective_head_state tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("node_status", "min_dep_status", "expected"),
    [
        ("planning", None, "planning"),
        ("planning", "pending", "planning"),
        ("in_progress", None, "in-progress"),
        ("in_progress", "pending", "in-progress"),
        ("pending", None, "ready"),
        ("pending", "done", "ready"),
        ("pending", "skipped", "ready"),
        ("pending", "planning", "planning"),
        ("pending", "in_progress", "in-progress"),
    ],
    ids=[
        "planning-no-deps",
        "planning-overrides-dep-status",
        "in_progress-no-deps",
        "in_progress-overrides-dep-status",
        "pending-no-deps-is-ready",
        "pending-deps-done-is-ready",
        "pending-deps-skipped-is-ready",
        "pending-dep-planning-shows-planning",
        "pending-dep-in_progress-shows-in-progress",
    ],
)
def test_compute_objective_head_state(
    node_status: str,
    min_dep_status: str | None,
    expected: str,
) -> None:
    assert compute_objective_head_state(node_status, min_dep_status) == expected
