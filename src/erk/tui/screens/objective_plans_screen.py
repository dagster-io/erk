"""Modal screen displaying plans associated with an objective."""

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.github.metadata.roadmap import parse_roadmap
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _extract_plan_ids_from_roadmap(body: str) -> set[int]:
    """Extract plan IDs from roadmap nodes in the objective body.

    Parses the roadmap frontmatter and collects PR references (e.g., "#8070")
    from each node, converting them to integer plan IDs.

    Args:
        body: The objective issue body containing roadmap metadata

    Returns:
        Set of plan issue numbers referenced in the roadmap
    """
    phases, _ = parse_roadmap(body)
    plan_ids: set[int] = set()
    for phase in phases:
        for node in phase.nodes:
            if node.pr is not None:
                pr_str = node.pr[1:] if node.pr.startswith("#") else node.pr
                if pr_str.isdigit():
                    plan_ids.add(int(pr_str))
    return plan_ids


class ObjectivePlansScreen(ModalScreen):
    """Modal screen displaying plans associated with an objective."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("o", "open_issue", "Open issue", show=False),
        Binding("enter", "open_issue", "Open issue", show=False),
        Binding("p", "open_pr", "Open PR", show=False),
        Binding("left", "noop", show=False),
        Binding("right", "noop", show=False),
    ]

    DEFAULT_CSS = """
    ObjectivePlansScreen {
        align: center middle;
    }

    #obj-plans-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #obj-plans-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #obj-plans-title {
        text-style: bold;
        color: $primary;
    }

    #obj-plans-summary {
        color: $text;
    }

    #obj-plans-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #obj-plans-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #obj-plans-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #obj-plans-loading {
        color: $text-muted;
        text-style: italic;
    }

    #obj-plans-empty {
        color: $text-muted;
        text-style: italic;
    }

    #obj-plans-error {
        color: $error;
        text-style: italic;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        objective_id: int,
        objective_title: str,
        progress_display: str,
        objective_body: str,
    ) -> None:
        """Initialize with objective metadata and provider for async loading.

        Args:
            provider: Data provider for fetching plans
            objective_id: The objective issue number
            objective_title: The objective title for display
            progress_display: Progress display string (e.g., "3/7")
            objective_body: The raw objective issue body (for roadmap extraction)
        """
        super().__init__()
        self._provider = provider
        self._objective_id = objective_id
        self._objective_title = objective_title
        self._progress_display = progress_display
        self._objective_body = objective_body
        self._rows: list[PlanRowData] = []

    def compose(self) -> ComposeResult:
        """Create the objective plans dialog content."""
        with Vertical(id="obj-plans-dialog"):
            with Vertical(id="obj-plans-header"):
                yield Label(
                    f"Objective #{self._objective_id} Plans",
                    id="obj-plans-title",
                )
                yield Label(
                    f"{self._objective_title}  ({self._progress_display})",
                    id="obj-plans-summary",
                    markup=False,
                )

            yield Label("", id="obj-plans-divider")

            with Container(id="obj-plans-content-container"):
                yield Label("Loading plans...", id="obj-plans-loading")
                yield PlanDataTable(PlanFilters.default())

            yield Label("Press Esc, q, or Space to close", id="obj-plans-footer")

    def on_mount(self) -> None:
        """Fetch plans when screen mounts."""
        table = self.query_one(PlanDataTable)
        table.display = False
        self._fetch_plans()

    @work(thread=True)
    def _fetch_plans(self) -> None:
        """Fetch plans for this objective in background thread."""
        plans: list[PlanRowData] = []
        error: str | None = None

        # Error boundary: catch all exceptions from API operations to display
        # them in the UI rather than crashing the TUI.
        try:
            roadmap_plan_ids = _extract_plan_ids_from_roadmap(self._objective_body)
            if roadmap_plan_ids:
                plans = self._provider.fetch_plans_by_ids(roadmap_plan_ids)
            else:
                plans = self._provider.fetch_plans_for_objective(self._objective_id)
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_plans_loaded, plans, error)

    def _on_plans_loaded(self, plans: list[PlanRowData], error: str | None) -> None:
        """Handle plans loaded - update the display.

        Args:
            plans: The fetched plan rows
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#obj-plans-content-container", Container)

        # Remove the loading label
        container.query_one("#obj-plans-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="obj-plans-error"))
        elif plans:
            self._rows = plans
            table = self.query_one(PlanDataTable)
            table.populate(plans)
            table.display = True
            table.focus()
        else:
            container.mount(Label("(No plans found for this objective)", id="obj-plans-empty"))

    def action_noop(self) -> None:
        """No-op action to intercept left/right arrows."""

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j key)."""
        table = self.query_one(PlanDataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k key)."""
        table = self.query_one(PlanDataTable)
        table.action_cursor_up()

    def _get_selected_row(self) -> PlanRowData | None:
        """Get the PlanRowData for the currently selected row.

        Returns:
            PlanRowData for selected row, or None if no selection
        """
        table = self.query_one(PlanDataTable)
        return table.get_selected_row_data()

    def action_open_issue(self) -> None:
        """Open selected plan's issue in browser."""
        row = self._get_selected_row()
        if row is not None and row.plan_url:
            self._provider.browser.launch(row.plan_url)

    def action_open_pr(self) -> None:
        """Open selected plan's PR in browser."""
        row = self._get_selected_row()
        if row is not None and row.pr_url:
            self._provider.browser.launch(row.pr_url)

    @on(PlanDataTable.PlanClicked)
    def on_plan_clicked(self, event: PlanDataTable.PlanClicked) -> None:
        """Handle click on plan cell - open issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.plan_url:
                self._provider.browser.launch(row.plan_url)

    @on(PlanDataTable.PrClicked)
    def on_pr_clicked(self, event: PlanDataTable.PrClicked) -> None:
        """Handle click on pr cell - open PR in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)

    @on(PlanDataTable.RunIdClicked)
    def on_run_id_clicked(self, event: PlanDataTable.RunIdClicked) -> None:
        """Handle click on run-id cell - open run URL in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.run_url:
                self._provider.browser.launch(row.run_url)

    @on(PlanDataTable.LocalWtClicked)
    def on_local_wt_clicked(self, event: PlanDataTable.LocalWtClicked) -> None:
        """Handle click on local-wt cell - copy worktree name to clipboard."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.worktree_name:
                success = self._provider.clipboard.copy(row.worktree_name)
                if success:
                    self.notify(f"Copied: {row.worktree_name}", timeout=2)
                else:
                    self.notify("Clipboard unavailable", severity="error", timeout=2)

    @on(PlanDataTable.BranchClicked)
    def on_branch_clicked(self, event: PlanDataTable.BranchClicked) -> None:
        """Handle click on branch cell - copy branch name to clipboard."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            branch = row.pr_head_branch or row.worktree_branch
            if branch:
                success = self._provider.clipboard.copy(branch)
                if success:
                    self.notify(f"Copied: {branch}", timeout=2)
                else:
                    self.notify("Clipboard unavailable", severity="error", timeout=2)
