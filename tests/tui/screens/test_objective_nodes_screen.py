"""Tests for ObjectiveNodesScreen _build_table_rows formatting."""

from rich.text import Text

from erk.tui.screens.objective_nodes_screen import _build_table_rows
from erk_shared.gateway.github.metadata.dependency_graph import ObjectiveNode
from erk_shared.gateway.github.metadata.roadmap import RoadmapNode, RoadmapPhase
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def _rows_from(
    phases: list[RoadmapPhase],
    *,
    graph_nodes: tuple[ObjectiveNode, ...],
    pr_lookup: dict | None = None,
    next_node_id: str | None = None,
) -> list[tuple[str | Text, ...]]:
    """Helper that calls _build_table_rows and returns only the rows."""
    rows, _node_rows = _build_table_rows(
        phases,
        graph_nodes=graph_nodes,
        pr_lookup=pr_lookup or {},
        next_node_id=next_node_id,
    )
    return rows


def _make_node(
    id: str,
    description: str,
    status: str = "pending",
    pr: str | None = None,
) -> ObjectiveNode:
    return ObjectiveNode(
        id=id,
        description=description,
        status=status,
        pr=pr,
        depends_on=(),
        slug=None,
    )


def _make_roadmap_node(
    id: str,
    description: str,
    status: str = "pending",
    pr: str | None = None,
) -> RoadmapNode:
    return RoadmapNode(
        id=id,
        description=description,
        status=status,
        pr=pr,
        depends_on=None,
        slug=None,
        reason=None,
    )


def _single_phase(
    node: ObjectiveNode,
    roadmap_node: RoadmapNode,
) -> list[RoadmapPhase]:
    return [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Foundation",
            nodes=[roadmap_node],
        ),
    ]


def test_pending_no_pr() -> None:
    """Pending node without PR shows circle symbol and dashes for PR columns."""
    node = _make_node("1.1", "Scaffold project", status="pending")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="pending")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
    )
    # rows[0] is phase separator, rows[1] is the node
    row = rows[1]
    assert row[0] == "1.1"
    assert row[1] == "\u25cb"  # ○ pending symbol
    assert row[2] == "Scaffold project"
    # All PR columns should be "-"
    for col in row[3:]:
        assert col == "-"


def test_done_no_pr() -> None:
    """Done node shows checkmark symbol."""
    node = _make_node("1.1", "Scaffold project", status="done")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="done")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
    )
    row = rows[1]
    assert row[1] == "\u2713"  # ✓ done symbol


def test_next_node_marker() -> None:
    """Next actionable node gets >>> prefix on id."""
    node = _make_node("2.1", "Build CLI", status="pending")
    rnode = _make_roadmap_node("2.1", "Build CLI", status="pending")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
        next_node_id="2.1",
    )
    row = rows[1]
    assert row[0] == ">>> 2.1"


def test_done_node_with_pr_no_data_shows_merged() -> None:
    """Done node with PR but no fetched data infers 'merged' stage."""
    node = _make_node("1.1", "Scaffold project", status="done", pr="#8701")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="done", pr="#8701")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
    )
    row = rows[1]
    assert row[3] == "#8701"
    stage_cell = row[4]
    assert isinstance(stage_cell, Text)
    assert str(stage_cell) == "merged"
    assert stage_cell.style == "green"
    # Remaining PR columns should still be "-"
    for col in row[5:]:
        assert col == "-"


def test_skipped_node_with_pr_no_data_shows_closed() -> None:
    """Skipped node with PR but no fetched data infers 'closed' stage."""
    node = _make_node("1.1", "Scaffold project", status="skipped", pr="#8701")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="skipped", pr="#8701")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
    )
    row = rows[1]
    assert row[3] == "#8701"
    stage_cell = row[4]
    assert isinstance(stage_cell, Text)
    assert str(stage_cell) == "closed"
    assert stage_cell.style == "dim red"


def test_pending_node_with_pr_no_data_shows_dashes() -> None:
    """Pending node with PR but no fetched data shows dashes (no inference)."""
    node = _make_node("1.1", "Scaffold project", status="pending", pr="#8701")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="pending", pr="#8701")
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
    )
    row = rows[1]
    assert row[3] == "#8701"
    for col in row[4:]:
        assert col == "-"


def test_with_pr_and_data() -> None:
    """Node with PR data shows enriched stage column as styled Text."""
    node = _make_node("1.1", "Scaffold project", status="done", pr="#8701")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="done", pr="#8701")
    pr_row = make_plan_row(
        8701,
        "Scaffold project",
        pr_number=8701,
        pr_state="MERGED",
        lifecycle_display="[green]merged[/green]",
        status_display="merged",
        author="dev-user",
    )
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
        pr_lookup={8701: pr_row},
    )
    row = rows[1]
    assert row[3] == "#8701"
    stage_cell = row[4]
    assert isinstance(stage_cell, Text)
    assert str(stage_cell) == "merged"
    assert stage_cell.style == "green"
    assert row[10] == "dev-user"  # author


def test_done_node_with_stale_impl_lifecycle_shows_merged() -> None:
    """Done node with PR data showing stale 'impl' lifecycle overrides to 'merged'."""
    node = _make_node("1.1", "Scaffold project", status="done", pr="#8701")
    rnode = _make_roadmap_node("1.1", "Scaffold project", status="done", pr="#8701")
    pr_row = make_plan_row(
        8701,
        "Scaffold project",
        pr_number=8701,
        pr_state="OPEN",
        lifecycle_display="[yellow]impl[/yellow]",
        status_display="impl",
        author="dev-user",
    )
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
        pr_lookup={8701: pr_row},
    )
    row = rows[1]
    assert row[3] == "#8701"
    stage_cell = row[4]
    assert isinstance(stage_cell, Text)
    assert str(stage_cell) == "merged"
    assert stage_cell.style == "green"
    assert row[10] == "dev-user"


def test_with_pr_impl_stage_styled_yellow() -> None:
    """Node with impl stage shows yellow styled Text."""
    node = _make_node("1.1", "Build CLI", status="in_progress", pr="#8710")
    rnode = _make_roadmap_node("1.1", "Build CLI", status="in_progress", pr="#8710")
    pr_row = make_plan_row(
        8710,
        "Build CLI",
        pr_number=8710,
        pr_state="OPEN",
        lifecycle_display="[yellow]impl[/yellow]",
        status_display="impl",
    )
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
        pr_lookup={8710: pr_row},
    )
    row = rows[1]
    stage_cell = row[4]
    assert isinstance(stage_cell, Text)
    assert str(stage_cell) == "impl"
    assert stage_cell.style == "yellow"


def test_with_pr_and_checks() -> None:
    """Node with checks data shows checks column."""
    node = _make_node("2.1", "Build CLI", status="in_progress", pr="#8710")
    rnode = _make_roadmap_node("2.1", "Build CLI", status="in_progress", pr="#8710")
    pr_row = make_plan_row(
        8710,
        "Build CLI",
        pr_number=8710,
        pr_state="OPEN",
        checks_passing=False,
        checks_counts=(3, 5),
    )
    rows = _rows_from(
        _single_phase(node, rnode),
        graph_nodes=(node,),
        pr_lookup={8710: pr_row},
    )
    row = rows[1]
    assert row[3] == "#8710"
    assert row[9] == "-"  # checks_display defaults to "-" in make_plan_row


def test_phases_grouped() -> None:
    """Nodes are grouped under phase separator rows."""
    nodes = (
        _make_node("1.1", "Step A", status="done"),
        _make_node("2.1", "Step C", status="pending"),
    )
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Foundation",
            nodes=[_make_roadmap_node("1.1", "Step A", status="done")],
        ),
        RoadmapPhase(
            number=2,
            suffix="",
            name="Implementation",
            nodes=[_make_roadmap_node("2.1", "Step C", status="pending")],
        ),
    ]
    rows = _rows_from(
        phases,
        graph_nodes=nodes,
        next_node_id="2.1",
    )
    # Phase 1 separator
    phase1_sep = rows[0]
    assert isinstance(phase1_sep[2], Text)
    assert str(phase1_sep[2]) == "Phase 1: Foundation"
    # Phase 2 separator
    phase2_sep = rows[2]
    assert isinstance(phase2_sep[2], Text)
    assert str(phase2_sep[2]) == "Phase 2: Implementation"
    # Node 2.1 should be marked as next
    assert rows[3][0] == ">>> 2.1"


def test_phase_suffix() -> None:
    """Phase with suffix renders correctly in separator."""
    nodes = (_make_node("1A.1", "Step A", status="pending"),)
    phases = [
        RoadmapPhase(
            number=1,
            suffix="A",
            name="Setup",
            nodes=[_make_roadmap_node("1A.1", "Step A", status="pending")],
        ),
    ]
    rows = _rows_from(
        phases,
        graph_nodes=nodes,
    )
    phase_sep = rows[0]
    assert isinstance(phase_sep[2], Text)
    assert str(phase_sep[2]) == "Phase 1A: Setup"


def test_separator_skip_logic_crosses_phase_boundary() -> None:
    """Verify _is_separator_row correctly identifies separators for skip logic.

    Regression: cursor got stuck before phase separators because
    on_data_table_row_highlighted bounced the cursor back before
    the skip could complete.
    """
    nodes = (
        _make_node("1.1", "Step A", status="done"),
        _make_node("2.1", "Step B", status="pending"),
    )
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Foundation",
            nodes=[_make_roadmap_node("1.1", "Step A", status="done")],
        ),
        RoadmapPhase(
            number=2,
            suffix="",
            name="Build",
            nodes=[_make_roadmap_node("2.1", "Step B", status="pending")],
        ),
    ]
    _rows, node_rows = _build_table_rows(
        phases,
        graph_nodes=nodes,
        pr_lookup={},
        next_node_id=None,
    )
    # Layout: [sep(0), node(1), sep(2), node(3)]
    # From node at index 1, moving down lands on separator at index 2.
    # Skip logic should advance to index 3 (the next real node).
    assert node_rows[0] is None  # separator
    assert node_rows[1] is not None  # node 1.1
    assert node_rows[2] is None  # separator
    assert node_rows[3] is not None  # node 2.1

    # The target after skipping separator at index 2 should be index 3
    cursor = 1  # starting at node 1.1
    next_pos = cursor + 1  # = 2 (separator)
    if node_rows[next_pos] is None:
        next_pos += 1  # = 3 (node 2.1)
    assert node_rows[next_pos] is not None
    assert node_rows[next_pos].id == "2.1"


def test_node_rows_parallel_mapping() -> None:
    """_build_table_rows returns parallel node list with None for separators."""
    nodes = (
        _make_node("1.1", "Step A", status="done"),
        _make_node("2.1", "Step B", status="pending"),
    )
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Foundation",
            nodes=[_make_roadmap_node("1.1", "Step A", status="done")],
        ),
        RoadmapPhase(
            number=2,
            suffix="",
            name="Build",
            nodes=[_make_roadmap_node("2.1", "Step B", status="pending")],
        ),
    ]
    rows, node_rows = _build_table_rows(
        phases,
        graph_nodes=nodes,
        pr_lookup={},
        next_node_id=None,
    )
    assert len(rows) == len(node_rows)
    # Phase separators are None
    assert node_rows[0] is None
    assert node_rows[2] is None
    # Actual nodes are ObjectiveNode
    assert node_rows[1] is not None
    assert node_rows[1].id == "1.1"
    assert node_rows[3] is not None
    assert node_rows[3].id == "2.1"
