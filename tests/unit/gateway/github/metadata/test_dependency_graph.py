"""Unit tests for dependency_graph sparkline and find_graph_next_node."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
    build_state_sparkline,
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
