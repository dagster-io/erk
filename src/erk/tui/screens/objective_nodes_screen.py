"""Modal screen displaying objective node breakdown with PR status."""

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label

from erk.core.display_utils import strip_rich_markup
from erk.tui.data.types import PlanRowData
from erk_shared.gateway.github.metadata.dependency_graph import (
    _STATUS_SYMBOLS,
    ObjectiveNode,
    parse_graph,
)
from erk_shared.gateway.github.metadata.roadmap import RoadmapPhase
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _build_table_rows(
    phases: list[RoadmapPhase],
    *,
    graph_nodes: tuple[ObjectiveNode, ...],
    pr_lookup: dict[int, PlanRowData],
    next_node_id: str | None,
) -> list[tuple[str | Text, ...]]:
    """Build table row tuples grouped by phase.

    Args:
        phases: Roadmap phases for grouping
        graph_nodes: All graph nodes
        pr_lookup: Mapping of PR number to PlanRowData
        next_node_id: ID of the next actionable node

    Returns:
        List of row tuples matching column order:
        (id, sts, description, pr, stage, sts2, branch, run-id, run, chks, author)
    """
    empty_pr_cols = ("-", "-", "-", "-", "-", "-", "-")
    node_map = {n.id: n for n in graph_nodes}
    rows: list[tuple[str | Text, ...]] = []

    for phase in phases:
        # Phase separator row (11 columns)
        phase_label = Text(f"Phase {phase.number}{phase.suffix}: {phase.name}", style="bold")
        rows.append(("", "", phase_label, "", "", "", "", "", "", "", ""))

        for roadmap_node in phase.nodes:
            obj_node = node_map.get(roadmap_node.id)
            if obj_node is None:
                continue

            is_next = obj_node.id == next_node_id
            id_cell = f">>> {obj_node.id}" if is_next else obj_node.id
            symbol = _STATUS_SYMBOLS.get(obj_node.status, "?")
            desc = obj_node.description[:30]

            # PR-related columns default
            pr_cell = "-"
            pr_enriched = empty_pr_cols

            if obj_node.pr is not None:
                pr_str = obj_node.pr.lstrip("#")
                if pr_str.isdigit():
                    pr_num = int(pr_str)
                    pr_cell = f"#{pr_num}"
                    pr_data = pr_lookup.get(pr_num)
                    if pr_data is not None:
                        stage = strip_rich_markup(pr_data.lifecycle_display)
                        status = pr_data.status_display
                        branch = pr_data.pr_head_branch or pr_data.worktree_branch or "-"
                        run_id = strip_rich_markup(pr_data.run_id_display)
                        run_text = strip_rich_markup(pr_data.run_state_display)
                        run_emoji = run_text.split(" ", 1)[0] if run_text.strip() else "-"
                        chks = strip_rich_markup(pr_data.checks_display)
                        author = pr_data.author
                        pr_enriched = (stage, status, branch, run_id, run_emoji, chks, author)

            rows.append((id_cell, symbol, desc, pr_cell, *pr_enriched))

    return rows


class ObjectiveNodesScreen(ModalScreen):
    """Modal screen displaying objective node breakdown."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    DEFAULT_CSS = """
    ObjectiveNodesScreen {
        align: center middle;
    }

    #nodes-dialog {
        width: 90%;
        max-width: 160;
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

    #nodes-table {
        width: 100%;
        height: 1fr;
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

    def action_cursor_down(self) -> None:
        table = self.query_one("#nodes-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#nodes-table", DataTable)
        table.action_cursor_up()

    @work(thread=True)
    def _fetch_nodes(self) -> None:
        """Parse objective body and fetch PR details in background thread."""
        error: str | None = None
        table_rows: list[tuple[str | Text, ...]] = []

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
                        pr_str = node.pr.lstrip("#")
                        if pr_str.isdigit():
                            pr_numbers.add(int(pr_str))

                # Fetch PR data
                pr_lookup: dict[int, PlanRowData] = {}
                if pr_numbers:
                    pr_rows = self._provider.fetch_plans_by_ids(pr_numbers)
                    pr_lookup = {row.plan_id: row for row in pr_rows}

                table_rows = _build_table_rows(
                    phases,
                    graph_nodes=graph.nodes,
                    pr_lookup=pr_lookup,
                    next_node_id=next_node_id,
                )
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_nodes_loaded, table_rows, error)

    def _on_nodes_loaded(self, table_rows: list[tuple[str | Text, ...]], error: str | None) -> None:
        """Handle nodes loaded - populate the DataTable.

        Args:
            table_rows: List of row tuples for the table
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#nodes-content-container", Container)
        container.query_one("#nodes-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="nodes-error"))
            return

        if not table_rows:
            container.mount(Label("(No nodes found)", id="nodes-error"))
            return

        table = DataTable(id="nodes-table", cursor_type="row")
        container.mount(table)

        table.add_column("id", key="id", width=6)
        table.add_column("sts", key="sts", width=3)
        table.add_column("description", key="description", width=30)
        table.add_column("pr", key="pr", width=6)
        table.add_column("stage", key="stage", width=8)
        table.add_column("sts", key="sts2", width=7)
        table.add_column("branch", key="branch", width=35)
        table.add_column("run-id", key="run_id", width=10)
        table.add_column("run", key="run", width=3)
        table.add_column("chks", key="chks", width=5)
        table.add_column("author", key="author", width=9)

        for row in table_rows:
            table.add_row(*row)
