"""Tests for ObjectiveNodesScreen formatting and display."""

from erk.tui.screens.objective_nodes_screen import _format_node_line, _format_nodes_by_phase
from erk_shared.gateway.github.metadata.dependency_graph import ObjectiveNode
from erk_shared.gateway.github.metadata.roadmap import RoadmapNode, RoadmapPhase
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


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
    )


def test_format_node_line_pending_no_pr() -> None:
    """Pending node without PR shows status symbol and description."""
    node = _make_node("1.1", "Scaffold project", status="pending")
    line = _format_node_line(node, pr_lookup={}, is_next=False)
    assert "**1.1**" in line
    assert "pending" in line
    assert "Scaffold project" in line
    assert line.startswith("  -")


def test_format_node_line_done_no_pr() -> None:
    """Done node shows check symbol."""
    node = _make_node("1.1", "Scaffold project", status="done")
    line = _format_node_line(node, pr_lookup={}, is_next=False)
    assert "\u2713" in line  # checkmark


def test_format_node_line_next_node_marker() -> None:
    """Next actionable node gets >>> marker."""
    node = _make_node("2.1", "Build CLI", status="pending")
    line = _format_node_line(node, pr_lookup={}, is_next=True)
    assert line.startswith(">>>")


def test_format_node_line_with_pr_no_data() -> None:
    """Node with PR reference but no fetched data shows just PR number."""
    node = _make_node("1.1", "Scaffold project", status="done", pr="#8701")
    line = _format_node_line(node, pr_lookup={}, is_next=False)
    assert "#8701" in line


def test_format_node_line_with_pr_and_data() -> None:
    """Node with PR data shows state and checks."""
    node = _make_node("1.1", "Scaffold project", status="done", pr="#8701")
    pr_row = make_plan_row(
        8701,
        "Scaffold project",
        pr_number=8701,
        pr_state="MERGED",
        checks_passing=True,
        checks_counts=(5, 5),
    )
    line = _format_node_line(node, pr_lookup={8701: pr_row}, is_next=False)
    assert "#8701" in line
    assert "MERGED" in line


def test_format_node_line_with_pr_and_checks() -> None:
    """Node with failing checks shows check info."""
    node = _make_node("2.1", "Build CLI", status="in_progress", pr="#8710")
    pr_row = make_plan_row(
        8710,
        "Build CLI",
        pr_number=8710,
        pr_state="OPEN",
        checks_passing=False,
        checks_counts=(3, 5),
    )
    line = _format_node_line(node, pr_lookup={8710: pr_row}, is_next=False)
    assert "#8710" in line
    assert "OPEN" in line
    assert "checks:3/5" in line


def test_format_nodes_by_phase_groups_correctly() -> None:
    """Nodes are grouped under phase headers."""
    nodes = (
        _make_node("1.1", "Step A", status="done", pr="#100"),
        _make_node("1.2", "Step B", status="done"),
        _make_node("2.1", "Step C", status="pending"),
    )
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Foundation",
            nodes=[
                _make_roadmap_node("1.1", "Step A", status="done", pr="#100"),
                _make_roadmap_node("1.2", "Step B", status="done"),
            ],
        ),
        RoadmapPhase(
            number=2,
            suffix="",
            name="Implementation",
            nodes=[
                _make_roadmap_node("2.1", "Step C", status="pending"),
            ],
        ),
    ]
    result = _format_nodes_by_phase(
        phases,
        graph_nodes=nodes,
        pr_lookup={},
        next_node_id="2.1",
    )
    assert "## Phase 1: Foundation" in result
    assert "## Phase 2: Implementation" in result
    assert "**1.1**" in result
    assert "**2.1**" in result
    # 2.1 should be marked as next
    assert ">>> **2.1**" in result


def test_format_nodes_by_phase_with_suffix() -> None:
    """Phase with suffix renders correctly."""
    nodes = (_make_node("1A.1", "Step A", status="pending"),)
    phases = [
        RoadmapPhase(
            number=1,
            suffix="A",
            name="Setup",
            nodes=[
                _make_roadmap_node("1A.1", "Step A", status="pending"),
            ],
        ),
    ]
    result = _format_nodes_by_phase(
        phases,
        graph_nodes=nodes,
        pr_lookup={},
        next_node_id=None,
    )
    assert "## Phase 1A: Setup" in result
