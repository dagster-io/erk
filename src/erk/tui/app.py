"""Main Textual application for erk dash interactive mode."""

import asyncio
import time
from datetime import datetime
from pathlib import Path

import click
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Header, Label

from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    .help-section {
        margin-top: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $primary;
    }

    .help-binding {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help dialog content."""
        with Vertical(id="help-dialog"):
            yield Label("erk dash - Keyboard Shortcuts", id="help-title")

            with Vertical(classes="help-section"):
                yield Label("Navigation", classes="help-section-title")
                yield Label("↑/k     Move cursor up", classes="help-binding")
                yield Label("↓/j     Move cursor down", classes="help-binding")
                yield Label("Home    Jump to first row", classes="help-binding")
                yield Label("End     Jump to last row", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Actions", classes="help-section-title")
                yield Label("Enter/o Open issue in browser", classes="help-binding")
                yield Label("p       Open PR in browser", classes="help-binding")
                yield Label("c       Copy checkout command", classes="help-binding")
                yield Label("i       Show implement command", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("General", classes="help-section-title")
                yield Label("r       Refresh data", classes="help-binding")
                yield Label("?       Show this help", classes="help-binding")
                yield Label("q/Esc   Quit", classes="help-binding")

            yield Label("")
            yield Label("Press any key to close", id="help-footer")


class ErkDashApp(App):
    """Interactive TUI for erk dash command.

    Displays plans in a navigable table with quick actions.
    """

    CSS_PATH = Path(__file__).parent / "styles" / "dash.tcss"

    BINDINGS = [
        Binding("q", "exit_app", "Quit"),
        Binding("escape", "exit_app", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "open_issue", "Open Issue"),
        Binding("o", "open_issue", "Open Issue", show=False),
        Binding("p", "open_pr", "Open PR"),
        Binding("c", "copy_checkout", "Copy Checkout"),
        Binding("i", "show_implement", "Implement"),
    ]

    def __init__(
        self,
        provider: PlanDataProvider,
        filters: PlanFilters,
        refresh_interval: float = 15.0,
    ) -> None:
        """Initialize the dashboard app.

        Args:
            provider: Data provider for fetching plan data
            filters: Filter options for the plan list
            refresh_interval: Seconds between auto-refresh (0 to disable)
        """
        super().__init__()
        self._provider = provider
        self._plan_filters = filters
        self._refresh_interval = refresh_interval
        self._table: PlanDataTable | None = None
        self._status_bar: StatusBar | None = None
        self._rows: list[PlanRowData] = []
        self._refresh_task: asyncio.Task | None = None
        self._loading = True

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Label("Loading plans...", id="loading-message")
            yield PlanDataTable(self._plan_filters)
        yield StatusBar()

    def on_mount(self) -> None:
        """Initialize app after mounting."""
        self._table = self.query_one(PlanDataTable)
        self._status_bar = self.query_one(StatusBar)
        self._loading_label = self.query_one("#loading-message", Label)

        # Hide table until loaded
        self._table.display = False

        # Start data loading
        self.run_worker(self._load_data(), exclusive=True)

        # Start refresh timer if interval > 0
        if self._refresh_interval > 0:
            self._start_refresh_timer()

    async def _load_data(self) -> None:
        """Load plan data in background thread."""
        # Track fetch timing
        start_time = time.monotonic()

        # Run sync fetch in executor to avoid blocking
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, self._provider.fetch_plans, self._plan_filters)

        # Calculate duration
        duration = time.monotonic() - start_time
        update_time = datetime.now().strftime("%H:%M:%S")

        # Update UI directly since we're in async context
        self._update_table(rows, update_time, duration)

    def _update_table(
        self,
        rows: list[PlanRowData],
        update_time: str | None = None,
        duration: float | None = None,
    ) -> None:
        """Update table with new data.

        Args:
            rows: Plan data to display
            update_time: Formatted time of this update
            duration: Duration of the fetch in seconds
        """
        self._rows = rows
        self._loading = False

        if self._table is not None:
            self._loading_label.display = False
            self._table.display = True
            self._table.populate(rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(rows))
            if update_time is not None:
                self._status_bar.set_last_update(update_time, duration)

    def _start_refresh_timer(self) -> None:
        """Start the auto-refresh countdown timer."""
        self._seconds_remaining = int(self._refresh_interval)
        self.set_interval(1.0, self._tick_countdown)

    def _tick_countdown(self) -> None:
        """Handle countdown timer tick."""
        if self._status_bar is not None:
            self._status_bar.set_refresh_countdown(self._seconds_remaining)

        self._seconds_remaining -= 1
        if self._seconds_remaining <= 0:
            self.action_refresh()
            self._seconds_remaining = int(self._refresh_interval)

    def action_exit_app(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Refresh plan data and reset countdown timer."""
        # Reset countdown timer
        if self._refresh_interval > 0:
            self._seconds_remaining = int(self._refresh_interval)
        self.run_worker(self._load_data(), exclusive=True)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j key)."""
        if self._table is not None:
            self._table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k key)."""
        if self._table is not None:
            self._table.action_cursor_up()

    def action_open_issue(self) -> None:
        """Open selected issue in browser."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.issue_url:
            click.launch(row.issue_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened issue #{row.issue_number}")

    def action_open_pr(self) -> None:
        """Open selected PR in browser."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            click.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        else:
            if self._status_bar is not None:
                self._status_bar.set_message("No PR linked to this plan")

    def action_show_implement(self) -> None:
        """Show implement command in status bar."""
        row = self._get_selected_row()
        if row is None:
            return

        cmd = f"erk implement {row.issue_number}"
        if self._status_bar is not None:
            self._status_bar.set_message(f"Copy: {cmd}")

    def action_copy_checkout(self) -> None:
        """Copy checkout command for selected row."""
        row = self._get_selected_row()
        if row is None:
            return
        self._copy_checkout_command(row)

    def _copy_checkout_command(self, row: PlanRowData) -> None:
        """Copy appropriate checkout command based on row state.

        If worktree exists locally, copies 'erk co {worktree_name}'.
        If only PR available, copies 'erk pr co #{pr_number}'.
        Shows status message with result.

        Args:
            row: The plan row data to generate command from
        """
        # Determine which command to use
        if row.exists_locally:
            # Local worktree exists - use branch checkout
            cmd = f"erk co {row.worktree_name}"
        elif row.pr_number is not None:
            # No local worktree but PR exists - use PR checkout
            cmd = f"erk pr co #{row.pr_number}"
        else:
            # Neither available
            if self._status_bar is not None:
                self._status_bar.set_message("No worktree or PR available for checkout")
            return

        # Copy to clipboard
        success = self._provider.clipboard.copy(cmd)

        # Show status message
        if self._status_bar is not None:
            if success:
                self._status_bar.set_message(f"Copied: {cmd}")
            else:
                self._status_bar.set_message(f"Clipboard unavailable. Copy manually: {cmd}")

    def _get_selected_row(self) -> PlanRowData | None:
        """Get currently selected row data."""
        if self._table is None:
            return None
        return self._table.get_selected_row_data()

    @on(PlanDataTable.RowSelected)
    def on_row_selected(self, event: PlanDataTable.RowSelected) -> None:
        """Handle Enter/double-click on row - open issue."""
        self.action_open_issue()

    @on(PlanDataTable.LocalWtClicked)
    def on_local_wt_clicked(self, event: PlanDataTable.LocalWtClicked) -> None:
        """Handle click on local-wt cell - copy checkout command.

        Args:
            event: LocalWtClicked event with row index
        """
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            self._copy_checkout_command(row)

    @on(PlanDataTable.RunIdClicked)
    def on_run_id_clicked(self, event: PlanDataTable.RunIdClicked) -> None:
        """Handle click on run-id cell - open run in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.run_url:
                click.launch(row.run_url)
                if self._status_bar is not None:
                    # Extract run ID from URL to avoid Rich markup in status bar
                    run_id = row.run_url.rsplit("/", 1)[-1]
                    self._status_bar.set_message(f"Opened run {run_id}")
