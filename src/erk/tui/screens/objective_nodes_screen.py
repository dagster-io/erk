"""Modal screen displaying objective node breakdown with PR status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label

from erk.core.display_utils import strip_rich_markup
from erk.tui.commands.provider import NodeCommandProvider
from erk.tui.commands.registry import get_copy_text
from erk.tui.commands.types import CommandContext
from erk.tui.data.types import PrRowData
from erk.tui.screens.launch_screen import LaunchScreen
from erk.tui.views.types import ViewMode
from erk_shared.gateway.github.metadata.dependency_graph import (
    _STATUS_SYMBOLS,
    ObjectiveNode,
    parse_graph,
)
from erk_shared.gateway.github.metadata.roadmap import RoadmapPhase
from erk_shared.gateway.plan_data_provider.abc import PrDataProvider
from erk_shared.gateway.pr_service.abc import PrService

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


def _styled_stage(lifecycle_display: str) -> str | Text:
    """Convert lifecycle display markup to a styled Text for DataTable.

    Args:
        lifecycle_display: Rich markup string from lifecycle display

    Returns:
        Styled Text object, or plain string if no known stage
    """
    plain = strip_rich_markup(lifecycle_display)
    if "merged" in lifecycle_display:
        return Text(plain, style="green")
    if "impl" in lifecycle_display:
        return Text(plain, style="yellow")
    if "planned" in lifecycle_display:
        return Text(plain, style="dim")
    if "closed" in lifecycle_display:
        return Text(plain, style="dim red")
    if "magenta" in lifecycle_display:
        return Text(plain, style="magenta")
    return plain


def _stage_from_node_status(status: str) -> Text | None:
    """Infer a styled stage cell from objective node status.

    Used when a node references a PR but fetch_prs_by_ids did not
    return data for it (e.g., the PR is already merged or closed).
    """
    if status == "done":
        return Text("merged", style="green")
    if status == "skipped":
        return Text("closed", style="dim red")
    return None


def _build_table_rows(
    phases: list[RoadmapPhase],
    *,
    graph_nodes: tuple[ObjectiveNode, ...],
    pr_lookup: dict[int, PrRowData],
    next_node_id: str | None,
) -> tuple[list[tuple[str | Text, ...]], list[ObjectiveNode | None]]:
    """Build table row tuples grouped by phase.

    Args:
        phases: Roadmap phases for grouping
        graph_nodes: All graph nodes
        pr_lookup: Mapping of PR number to PrRowData
        next_node_id: ID of the next actionable node

    Returns:
        Tuple of (row tuples, parallel node list). Phase separators get None
        in the node list. Row tuples match column order:
        (id, sts, description, pr, stage, sts2, branch, run-id, run, chks, author)
    """
    empty_pr_cols = ("-", "-", "-", "-", "-", "-", "-")
    node_map = {n.id: n for n in graph_nodes}
    rows: list[tuple[str | Text, ...]] = []
    node_rows: list[ObjectiveNode | None] = []

    for phase in phases:
        # Phase separator row (11 columns)
        phase_label = Text(f"Phase {phase.number}{phase.suffix}: {phase.name}", style="bold")
        rows.append(("", "", phase_label, "", "", "", "", "", "", "", ""))
        node_rows.append(None)

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

            pr_str = obj_node.pr.lstrip("#") if obj_node.pr is not None else ""
            if pr_str.isdigit():
                pr_num = int(pr_str)
                pr_cell = f"#{pr_num}"
                pr_data = pr_lookup.get(pr_num)
                if pr_data is not None:
                    stage = _stage_from_node_status(obj_node.status) or _styled_stage(
                        pr_data.lifecycle_display
                    )
                    status = pr_data.status_display
                    branch = pr_data.pr_head_branch or pr_data.worktree_branch or "-"
                    run_id = strip_rich_markup(pr_data.run_id_display)
                    run_text = strip_rich_markup(pr_data.run_state_display)
                    run_emoji = run_text.split(" ", 1)[0] if run_text else "-"
                    chks = strip_rich_markup(pr_data.checks_display)
                    author = pr_data.author
                    pr_enriched = (stage, status, branch, run_id, run_emoji, chks, author)
                else:
                    # No PR data fetched — infer stage from node status
                    stage = _stage_from_node_status(obj_node.status)
                    if stage is not None:
                        pr_enriched = (stage, "-", "-", "-", "-", "-", "-")

            rows.append((id_cell, symbol, desc, pr_cell, *pr_enriched))
            node_rows.append(obj_node)

    return rows, node_rows


class ObjectiveNodesScreen(ModalScreen):
    """Modal screen displaying objective node breakdown."""

    COMMANDS = {NodeCommandProvider}

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("p", "open_pr", "Open PR", show=False),
        Binding("o", "open_objective", "Objective", show=False),
        Binding("enter", "open_detail", "Detail", show=False),
        Binding("l", "launch", "Launch", show=False),
        Binding("ctrl+p", "command_palette", "Commands", show=False),
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

    #nodes-table > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #nodes-table > .datatable--cursor {
        background: $accent;
        color: $text;
    }

    #nodes-table > .datatable--hover {
        background: $surface-lighten-1;
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
        provider: PrDataProvider,
        service: PrService,
        pr_number: int,
        pr_body: str,
        full_title: str,
    ) -> None:
        """Initialize with objective metadata and provider for async loading.

        Args:
            provider: Data provider for fetching PR details
            service: Plan service for browser/clipboard/repo_root access
            pr_number: The objective issue number
            pr_body: The objective body text with roadmap metadata
            full_title: The full objective title for display
        """
        super().__init__()
        self._provider = provider
        self._service = service
        self._pr_number = pr_number
        self._pr_body = pr_body
        self._full_title = full_title
        self._node_rows: list[ObjectiveNode | None] = []
        self._pr_lookup: dict[int, PrRowData] = {}
        self._last_valid_row: int = 1
        self._skipping_separator: bool = False

    def compose(self) -> ComposeResult:
        """Create the nodes dialog content."""
        with Vertical(id="nodes-dialog"):
            with Vertical(id="nodes-header"):
                yield Label(f"Objective #{self._pr_number} Nodes", id="nodes-title")
                yield Label(self._full_title, id="nodes-summary", markup=False)

            yield Label("", id="nodes-divider")

            with Container(id="nodes-content-container"):
                yield Label("Loading nodes...", id="nodes-loading")

            yield Label(
                "p: PR  o: objective  l: launch  Enter: detail  Ctrl+P: commands  Esc: close",
                id="nodes-footer",
            )

    def on_mount(self) -> None:
        """Fetch node data when screen mounts."""
        self._fetch_nodes()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Restore cursor when a phase separator row is highlighted (e.g. mouse click).

        The _skipping_separator flag suppresses bounce-back during keyboard
        navigation.  It is cleared here (not in the action methods) because
        Textual posts RowHighlighted asynchronously — the events arrive
        *after* action_cursor_down/up returns.
        """
        if event.cursor_row < 0 or event.cursor_row >= len(self._node_rows):
            return
        if self._node_rows[event.cursor_row] is not None:
            self._last_valid_row = event.cursor_row
            self._skipping_separator = False
            return
        # Separator row
        if self._skipping_separator:
            return
        # Separator clicked — restore to last valid row
        event.data_table.move_cursor(row=self._last_valid_row)

    def _is_separator_row(self, row_index: int) -> bool:
        """Check if a row index is a phase separator."""
        if row_index < 0 or row_index >= len(self._node_rows):
            return False
        return self._node_rows[row_index] is None

    def action_cursor_down(self) -> None:
        results = self.query("#nodes-table")
        if not results:
            return
        table = results.first(DataTable)
        prev = table.cursor_row
        self._skipping_separator = True
        table.action_cursor_down()
        if self._is_separator_row(table.cursor_row):
            table.action_cursor_down()
            if self._is_separator_row(table.cursor_row):
                table.move_cursor(row=prev)
        # If cursor didn't move (at table boundary), clear flag now since
        # no RowHighlighted event will fire to clear it.
        if table.cursor_row == prev:
            self._skipping_separator = False

    def action_cursor_up(self) -> None:
        results = self.query("#nodes-table")
        if not results:
            return
        table = results.first(DataTable)
        prev = table.cursor_row
        self._skipping_separator = True
        table.action_cursor_up()
        if self._is_separator_row(table.cursor_row):
            table.action_cursor_up()
            if self._is_separator_row(table.cursor_row):
                table.move_cursor(row=prev)
        if table.cursor_row == prev:
            self._skipping_separator = False

    def action_command_palette(self) -> None:
        """Open the command palette."""
        self.app.action_command_palette()

    def action_launch(self) -> None:
        """Open the launchpad for the selected node's PR."""
        row = self._get_selected_row()
        if row is None:
            return
        ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
        self.app.push_screen(LaunchScreen(ctx=ctx), self._on_launch_result)

    def _on_launch_result(self, command_id: str | None) -> None:
        """Handle result from LaunchScreen dismissal."""
        if command_id is not None:
            self.execute_command(command_id)

    def _get_selected_row(self) -> PrRowData | None:
        """Get PrRowData for the currently selected table row."""
        table_results = self.query("#nodes-table")
        if not table_results:
            return None
        table = table_results.first(DataTable)
        cursor_row = table.cursor_row
        if cursor_row < 0 or cursor_row >= len(self._node_rows):
            return None
        node = self._node_rows[cursor_row]
        if node is None or node.pr is None:
            return None
        pr_str = node.pr.lstrip("#")
        if not pr_str.isdigit():
            return None
        return self._pr_lookup.get(int(pr_str))

    def action_open_pr(self) -> None:
        """Open selected node's PR in browser.

        Uses pr_url if available, falls back to pr_url (which IS the PR URL
        for PR-based plans).
        """
        row = self._get_selected_row()
        if row is None:
            return
        url = row.pr_url
        if url is None:
            return
        self._service.browser.launch(url)

    def action_open_objective(self) -> None:
        """Open the parent objective issue in browser."""
        # Find any PrRowData to get the repo base URL
        for pr_data in self._pr_lookup.values():
            if pr_data.pr_url is not None:
                base_url = pr_data.pr_url.rsplit("/", 2)[0]
                objective_url = f"{base_url}/issues/{self._pr_number}"
                self._service.browser.launch(objective_url)
                return

    def action_open_detail(self) -> None:
        """Open PlanDetailScreen for the selected node."""
        row = self._get_selected_row()
        if row is None:
            return
        from erk.tui.screens.plan_detail_screen import PlanDetailScreen

        self.app.push_screen(
            PlanDetailScreen(
                row=row,
                clipboard=self._service.clipboard,
                browser=self._service.browser,
                repo_root=self._service.repo_root,
                view_mode=ViewMode.PLANS,
            )
        )

    def execute_command(self, command_id: str) -> None:
        """Execute a command from the palette or launchpad.

        Handles OPEN, COPY, and ACTION commands. ACTION commands dismiss
        the nodes screen and delegate to app-level async methods.

        Args:
            command_id: The ID of the command to execute
        """
        row = self._get_selected_row()
        if row is None:
            return

        if command_id == "open_issue":
            if row.pr_url:
                self._service.browser.launch(row.pr_url)
                self.notify(f"Opened plan #{row.pr_number}")

        elif command_id == "open_pr":
            url = row.pr_url
            if url:
                self._service.browser.launch(url)
                self.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                self._service.browser.launch(row.run_url)
                self.notify(f"Opened run {row.run_id_display}")

        elif command_id.startswith("copy_"):
            ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}", timeout=2)

        else:
            self._execute_action_command(command_id, row)

    def _dismiss_and_get_app(self) -> ErkDashApp | None:
        """Dismiss the screen and return the app if it is an ErkDashApp.

        Returns:
            The ErkDashApp instance, or None if the app is not an ErkDashApp.
        """
        from erk.tui.app import ErkDashApp

        self.dismiss()
        if isinstance(self.app, ErkDashApp):
            return self.app
        return None

    def _execute_action_command(self, command_id: str, row: PrRowData) -> None:
        """Execute an ACTION command by dismissing and delegating to app.

        Args:
            command_id: The ACTION command ID
            row: The selected row's plan data
        """
        if command_id == "close_pr":
            self._action_close_pr(row)
        elif command_id == "dispatch_to_queue":
            self._action_dispatch_to_queue(row)
        elif command_id == "land_pr":
            self._action_land_pr(row)
        elif command_id == "rebase_remote":
            self._action_rebase_remote(row)
        elif command_id == "address_remote":
            self._action_address_remote(row)
        elif command_id == "rewrite_remote":
            self._action_rewrite_remote(row)
        elif command_id in ("cmux_checkout", "cmux_teleport"):
            self._action_cmux_checkout(command_id, row)
        elif command_id == "incremental_dispatch":
            self._action_incremental_dispatch(row)

    def _action_close_pr(self, row: PrRowData) -> None:
        if row.pr_url is None:
            return
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"close-plan-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Closing plan #{row.pr_number}...")
        app._close_pr_async(op_id, row.pr_number, row.pr_url)

    def _action_dispatch_to_queue(self, row: PrRowData) -> None:
        if row.pr_url is None:
            return
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"dispatch-plan-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Dispatching plan #{row.pr_number} to queue...")
        app._dispatch_to_queue_async(op_id, row.pr_number)

    def _action_land_pr(self, row: PrRowData) -> None:
        if row.pr_number is None or row.pr_head_branch is None:
            return
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"land-pr-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Landing PR #{row.pr_number}...")
        learn_source_pr = row.pr_number if not row.is_learn_plan else None
        app._land_pr_async(
            op_id=op_id,
            pr_number=row.pr_number,
            branch=row.pr_head_branch,
            objective_issue=row.objective_issue,
            learn_source_pr=learn_source_pr,
        )

    def _action_rebase_remote(self, row: PrRowData) -> None:
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"rebase-pr-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Dispatching rebase for PR #{row.pr_number}...")
        app._rebase_remote_async(op_id, row.pr_number)

    def _action_address_remote(self, row: PrRowData) -> None:
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"address-pr-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Dispatching address for PR #{row.pr_number}...")
        app._address_remote_async(op_id, row.pr_number)

    def _action_rewrite_remote(self, row: PrRowData) -> None:
        app = self._dismiss_and_get_app()
        if app is None:
            return
        op_id = f"rewrite-pr-{row.pr_number}"
        app._start_operation(op_id=op_id, label=f"Dispatching rewrite for PR #{row.pr_number}...")
        app._rewrite_remote_async(op_id, row.pr_number)

    def _action_cmux_checkout(self, command_id: str, row: PrRowData) -> None:
        if row.pr_head_branch is None:
            return
        teleport = command_id == "cmux_teleport"
        app = self._dismiss_and_get_app()
        if app is None:
            return
        verb = "teleport" if teleport else "checkout"
        op_id = f"cmux-{verb}-{row.pr_number}"
        suffix = " (teleport)" if teleport else ""
        label = f"Creating cmux workspace{suffix} for PR #{row.pr_number}..."
        app._start_operation(op_id=op_id, label=label)
        app._cmux_checkout_async(op_id, row.pr_number, row.pr_head_branch, teleport=teleport)

    def _action_incremental_dispatch(self, row: PrRowData) -> None:
        app = self._dismiss_and_get_app()
        if app is None:
            return
        app.execute_palette_command("incremental_dispatch")

    @work(thread=True)
    def _fetch_nodes(self) -> None:
        """Parse objective body and fetch PR details in background thread."""
        error: str | None = None
        table_rows: list[tuple[str | Text, ...]] = []
        node_rows: list[ObjectiveNode | None] = []
        pr_lookup: dict[int, PrRowData] = {}

        try:
            result = parse_graph(self._pr_body)
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
                if pr_numbers:
                    pr_rows = self._provider.fetch_prs_by_ids(pr_numbers)
                    pr_lookup = {row.pr_number: row for row in pr_rows}

                table_rows, node_rows = _build_table_rows(
                    phases,
                    graph_nodes=graph.nodes,
                    pr_lookup=pr_lookup,
                    next_node_id=next_node_id,
                )
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_nodes_loaded, table_rows, node_rows, pr_lookup, error)

    def _on_nodes_loaded(
        self,
        table_rows: list[tuple[str | Text, ...]],
        node_rows: list[ObjectiveNode | None],
        pr_lookup: dict[int, PrRowData],
        error: str | None,
    ) -> None:
        """Handle nodes loaded - populate the DataTable.

        Args:
            table_rows: List of row tuples for the table
            node_rows: Parallel list mapping row index to ObjectiveNode (None for separators)
            pr_lookup: Mapping of PR number to PrRowData
            error: Error message if fetch failed, or None
        """
        self._node_rows = node_rows
        self._pr_lookup = pr_lookup
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

        # Move cursor past the initial phase separator row
        if self._is_separator_row(0):
            table.move_cursor(row=1)
