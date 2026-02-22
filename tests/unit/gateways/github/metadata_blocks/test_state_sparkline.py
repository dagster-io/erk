"""Unit tests for build_state_sparkline."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    ObjectiveNode,
    build_state_sparkline,
)


def _node(status: str) -> ObjectiveNode:
    """Create a minimal ObjectiveNode with the given status."""
    return ObjectiveNode(
        id="1.1",
        description="test",
        status=status,
        plan=None,
        pr=None,
        depends_on=(),
    )


def test_empty_nodes() -> None:
    """Empty node tuple produces empty string."""
    assert build_state_sparkline(()) == ""


def test_all_done() -> None:
    """All done nodes produce checkmarks."""
    nodes = tuple(_node("done") for _ in range(3))
    assert build_state_sparkline(nodes) == "✓✓✓"


def test_all_pending() -> None:
    """All pending nodes produce circles."""
    nodes = tuple(_node("pending") for _ in range(4))
    assert build_state_sparkline(nodes) == "○○○○"


def test_mixed_statuses() -> None:
    """Mixed statuses map correctly in position order."""
    nodes = (
        _node("done"),
        _node("done"),
        _node("done"),
        _node("in_progress"),
        _node("in_progress"),
        _node("pending"),
        _node("pending"),
        _node("pending"),
        _node("pending"),
    )
    assert build_state_sparkline(nodes) == "✓✓✓▶▶○○○○"


def test_planning_maps_to_active() -> None:
    """Planning status uses same symbol as in_progress."""
    nodes = (_node("planning"),)
    assert build_state_sparkline(nodes) == "▶"


def test_blocked_symbol() -> None:
    """Blocked status uses ⊘ symbol."""
    nodes = (_node("blocked"),)
    assert build_state_sparkline(nodes) == "⊘"


def test_skipped_symbol() -> None:
    """Skipped status uses - symbol."""
    nodes = (_node("skipped"),)
    assert build_state_sparkline(nodes) == "-"


def test_all_status_types() -> None:
    """All six status types produce correct symbols in order."""
    nodes = (
        _node("done"),
        _node("in_progress"),
        _node("planning"),
        _node("pending"),
        _node("blocked"),
        _node("skipped"),
    )
    assert build_state_sparkline(nodes) == "✓▶▶○⊘-"
