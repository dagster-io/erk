"""Unit tests for build_state_sparkline and build_frontier_sparkline."""

from erk_shared.gateway.github.metadata.dependency_graph import (
    ObjectiveNode,
    _compress_sparkline,
    build_frontier_sparkline,
    build_state_sparkline,
)


def _node(status: str) -> ObjectiveNode:
    """Create a minimal ObjectiveNode with the given status."""
    return ObjectiveNode(
        id="1.1",
        description="test",
        status=status,
        pr=None,
        depends_on=(),
        slug=None,
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


def test_planning_maps_to_half_circle() -> None:
    """Planning status uses ◐ symbol (distinct from in_progress ▶)."""
    nodes = (_node("planning"),)
    assert build_state_sparkline(nodes) == "◐"


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
    assert build_state_sparkline(nodes) == "✓▶◐○⊘-"


# build_frontier_sparkline tests


def test_frontier_all_done() -> None:
    """All done nodes produce '-' (no remaining work)."""
    nodes = tuple(_node("done") for _ in range(3))
    assert build_frontier_sparkline(nodes) == "-"


def test_frontier_short_pending() -> None:
    """Short runs stay as individual symbols (no compression)."""
    nodes = (
        _node("pending"),
        _node("pending"),
        _node("pending"),
    )
    assert build_frontier_sparkline(nodes) == "○○○"


def test_frontier_compresses_long_run() -> None:
    """Runs of >4 identical symbols get bracket-compressed."""
    nodes = tuple(_node("pending") for _ in range(13))
    assert build_frontier_sparkline(nodes) == "[13x○]"


def test_frontier_no_compress_at_four() -> None:
    """Run of exactly 4 is NOT compressed (need >4)."""
    nodes = tuple(_node("pending") for _ in range(4))
    assert build_frontier_sparkline(nodes) == "○○○○"


def test_frontier_compresses_five() -> None:
    """Run of 5 gets bracket-compressed (>4)."""
    nodes = (
        *(_node("pending") for _ in range(5)),
        _node("done"),
        _node("pending"),
    )
    assert build_frontier_sparkline(nodes) == "[5x○]✓○"


def test_frontier_compresses_later_run() -> None:
    """Compression applies to any run >4, not just the first."""
    nodes = (
        _node("in_progress"),
        *(_node("pending") for _ in range(8)),
    )
    assert build_frontier_sparkline(nodes) == "▶[8x○]"


def test_frontier_shows_done_nodes() -> None:
    """Done nodes are shown (not stripped), no compression for short runs."""
    nodes = (
        _node("done"),
        _node("done"),
        _node("done"),
        _node("in_progress"),
        _node("pending"),
        _node("pending"),
    )
    assert build_frontier_sparkline(nodes) == "✓✓✓▶○○"


def test_frontier_interleaved_statuses() -> None:
    """Interleaved statuses shown in full."""
    nodes = (
        _node("done"),
        _node("pending"),
        _node("done"),
        _node("pending"),
    )
    assert build_frontier_sparkline(nodes) == "✓○✓○"


def test_frontier_skipped_shown() -> None:
    """Skipped nodes are shown (not stripped)."""
    nodes = (
        _node("skipped"),
        _node("skipped"),
        _node("pending"),
        _node("pending"),
    )
    assert build_frontier_sparkline(nodes) == "--○○"


def test_frontier_empty_nodes() -> None:
    """Empty nodes tuple returns '-'."""
    assert build_frontier_sparkline(()) == "-"


def test_frontier_multiple_compressed_runs() -> None:
    """Multiple long runs each get bracket-compressed."""
    nodes = (
        *(_node("done") for _ in range(7)),
        _node("skipped"),
        *(_node("pending") for _ in range(14)),
    )
    assert build_frontier_sparkline(nodes) == "[7x✓]-[14x○]"


# _compress_sparkline direct tests


def test_compress_sparkline_empty() -> None:
    """Empty string passes through."""
    assert _compress_sparkline("") == ""


def test_compress_sparkline_single_char() -> None:
    """Single character passes through."""
    assert _compress_sparkline("✓") == "✓"


def test_compress_sparkline_short_run_not_compressed() -> None:
    """Runs of 4 or fewer are not compressed."""
    assert _compress_sparkline("○○○○") == "○○○○"


def test_compress_sparkline_five_compressed() -> None:
    """Run of exactly 5 gets bracket-compressed."""
    assert _compress_sparkline("○○○○○") == "[5x○]"


def test_compress_sparkline_mixed_runs() -> None:
    """Multiple long runs each get compressed independently."""
    assert _compress_sparkline("✓✓✓✓✓✓✓○○○○○○○○") == "[7x✓][8x○]"


def test_compress_sparkline_short_between_long() -> None:
    """Short runs between long runs stay uncompressed."""
    assert _compress_sparkline("✓✓✓✓✓✓✓-○○○○○○○○") == "[7x✓]-[8x○]"
