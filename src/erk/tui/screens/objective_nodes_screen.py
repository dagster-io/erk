"""Modal screen displaying objective node breakdown with PR status."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from erk.tui.data.types import PlanRowData
from erk_shared.gateway.github.metadata.dependency_graph import (
    _STATUS_SYMBOLS,
    ObjectiveNode,
    parse_graph,
)
from erk_shared.gateway.github.metadata.roadmap import RoadmapPhase
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _format_node_line(
    node: ObjectiveNode,
    *,
    pr_lookup: dict[int, PlanRowData],
    is_next: bool,
) -> str:
    """Format a single node as a markdown list item.

    Args:
        node: The objective node to format
        pr_lookup: Mapping of PR number to PlanRowData
        is_next: Whether this is the next actionable node

    Returns:
        Markdown list item string
    """
    symbol = _STATUS_SYMBOLS.get(node.status, "?")
    marker = ">>>" if is_next else "  -"
    desc = node.description[:50]
    status_str = node.status.replace("_", " ")

    if node.pr is None:
        return f"{marker} **{node.id}** {symbol} {status_str:<12} {desc}"

    pr_num = int(node.pr.lstrip("#"))
    pr_data = pr_lookup.get(pr_num)
    if pr_data is None:
        return f"{marker} **{node.id}** {symbol} {status_str:<12} {desc}  #{pr_num}"

    pr_state = pr_data.pr_state or "DRAFT"
    run_state = pr_data.run_state_display if pr_data.run_state_display != "-" else ""
    parts = [f"{marker} **{node.id}** {symbol} {status_str:<12} {desc}"]
    parts.append(f"  #{pr_num} {pr_state}")
    if pr_data.checks_counts is not None:
        passing, total = pr_data.checks_counts
        parts.append(f" checks:{passing}/{total}")
    if run_state:
        parts.append(f" run:{run_state}")
    return "".join(parts)


def _format_nodes_by_phase(
    phases: list[RoadmapPhase],
    *,
    graph_nodes: tuple[ObjectiveNode, ...],
    pr_lookup: dict[int, PlanRowData],
    next_node_id: str | None,
) -> str:
    """Format all nodes grouped by phase as markdown.

    Args:
        phases: Roadmap phases for grouping
        graph_nodes: All graph nodes (for looking up ObjectiveNode by ID)
        pr_lookup: Mapping of PR number to PlanRowData
        next_node_id: ID of the next actionable node (for highlighting)

    Returns:
        Markdown-formatted string with nodes grouped by phase
    """
    node_map = {n.id: n for n in graph_nodes}
    parts: list[str] = []

    for phase in phases:
        parts.append(f"## Phase {phase.number}{phase.suffix}: {phase.name}")
        parts.append("")
        for roadmap_node in phase.nodes:
            obj_node = node_map.get(roadmap_node.id)
            if obj_node is None:
                continue
            is_next = obj_node.id == next_node_id
            parts.append(_format_node_line(obj_node, pr_lookup=pr_lookup, is_next=is_next))
        parts.append("")

    return "\n".join(parts)


class ObjectiveNodesScreen(ModalScreen):
    """Modal screen displaying objective node breakdown."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    ObjectiveNodesScreen {
        align: center middle;
    }

    #nodes-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #nodes-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #nodes-title {
        text-style: bold;
        color: $primary;
    }

    #nodes-summary {
        color: $text;
    }

    #nodes-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #nodes-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #nodes-content {
        width: 100%;
    }

    #nodes-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #nodes-loading {
        color: $text-muted;
        text-style: italic;
    }

    #nodes-error {
        color: $error;
        text-style: italic;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        plan_id: int,
        plan_body: str,
        full_title: str,
    ) -> None:
        """Initialize with objective metadata and provider for async loading.

        Args:
            provider: Data provider for fetching PR details
            plan_id: The objective issue number
            plan_body: The objective body text with roadmap metadata
            full_title: The full objective title for display
        """
        super().__init__()
        self._provider = provider
        self._plan_id = plan_id
        self._plan_body = plan_body
        self._full_title = full_title

    def compose(self) -> ComposeResult:
        """Create the nodes dialog content."""
        with Vertical(id="nodes-dialog"):
            with Vertical(id="nodes-header"):
                yield Label(f"Objective #{self._plan_id} Nodes", id="nodes-title")
                yield Label(self._full_title, id="nodes-summary", markup=False)

            yield Label("", id="nodes-divider")

            with Container(id="nodes-content-container"):
                yield Label("Loading nodes...", id="nodes-loading")

            yield Label("Press Esc, q, or Space to close", id="nodes-footer")

    def on_mount(self) -> None:
        """Fetch node data when screen mounts."""
        self._fetch_nodes()

    @work(thread=True)
    def _fetch_nodes(self) -> None:
        """Parse objective body and fetch PR details in background thread."""
        error: str | None = None
        content: str = ""

        try:
            result = parse_graph(self._plan_body)
            if result is None:
                error = "No roadmap found in objective body"
            else:
                graph, phases, _errors = result
                next_node = graph.next_node()
                next_node_id = next_node.id if next_node is not None else None

                # Collect PR numbers from nodes
                pr_numbers: set[int] = set()
                for node in graph.nodes:
                    if node.pr is not None:
                        pr_numbers.add(int(node.pr.lstrip("#")))

                # Fetch PR data
                pr_lookup: dict[int, PlanRowData] = {}
                if pr_numbers:
                    pr_rows = self._provider.fetch_plans_by_ids(pr_numbers)
                    pr_lookup = {row.plan_id: row for row in pr_rows}

                content = _format_nodes_by_phase(
                    phases,
                    graph_nodes=graph.nodes,
                    pr_lookup=pr_lookup,
                    next_node_id=next_node_id,
                )
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_nodes_loaded, content, error)

    def _on_nodes_loaded(self, content: str, error: str | None) -> None:
        """Handle nodes loaded - update the display.

        Args:
            content: Formatted markdown content
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#nodes-content-container", Container)
        container.query_one("#nodes-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="nodes-error"))
            return

        if not content.strip():
            container.mount(Label("(No nodes found)", id="nodes-error"))
            return

        container.mount(Markdown(content, id="nodes-content"))
