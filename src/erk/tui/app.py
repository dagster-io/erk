"""Main Textual application for erk dash interactive mode."""

import asyncio
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.markup import escape as escape_markup
from textual import on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Click
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Input, Label, Static

from erk.tui.commands.executor import CommandExecutor
from erk.tui.commands.provider import PlanCommandProvider
from erk.tui.commands.real_executor import RealCommandExecutor
from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.filtering.logic import filter_plans
from erk.tui.filtering.types import FilterMode, FilterState
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from erk_shared.integrations.browser.abc import BrowserLauncher
    from erk_shared.integrations.clipboard.abc import Clipboard


class ClickableLink(Static):
    """A clickable link widget that opens a URL in the browser."""

    DEFAULT_CSS = """
    ClickableLink {
        color: $primary;
        text-style: underline;
    }
    ClickableLink:hover {
        color: $primary-lighten-2;
    }
    """

    def __init__(self, text: str, url: str, **kwargs) -> None:
        """Initialize clickable link.

        Args:
            text: Display text for the link
            url: URL to open when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(escape_markup(text), **kwargs)
        self._url = url

    def on_click(self, event: Click) -> None:
        """Open URL in browser when clicked."""
        event.stop()
        # Access browser through the app's provider (ErkDashApp)
        from erk.tui.app import ErkDashApp as _ErkDashApp

        app = self.app
        if isinstance(app, _ErkDashApp):
            app._provider.browser.launch(self._url)


class CopyableLabel(Static):
    """A label that copies text to clipboard when clicked, styled with orange/accent color."""

    DEFAULT_CSS = """
    CopyableLabel {
        color: $accent;
    }
    CopyableLabel:hover {
        color: $accent-lighten-1;
        text-style: bold;
    }
    """

    def __init__(self, label: str, text_to_copy: str, **kwargs) -> None:
        """Initialize copyable label.

        Args:
            label: Display text for the label (e.g., "[1]" or "erk pr co 2022")
            text_to_copy: Text to copy to clipboard when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(label, **kwargs)
        self._text_to_copy = text_to_copy
        self._original_label = label

    def on_click(self, event: Click) -> None:
        """Copy text to clipboard when clicked."""
        event.stop()
        success = self._copy_to_clipboard()
        if success:
            self.update("Copied!")
            self.set_timer(1.5, lambda: self.update(self._original_label))

    def _copy_to_clipboard(self) -> bool:
        """Copy text to clipboard, finding the clipboard interface.

        Returns:
            True if copy succeeded, False otherwise.
        """
        # Access clipboard through the app's provider (ErkDashApp)
        # Defer the isinstance check to avoid forward reference issues
        from erk.tui.app import ErkDashApp as _ErkDashApp

        app = self.app
        if isinstance(app, _ErkDashApp):
            return app._provider.clipboard.copy(self._text_to_copy)
        return False


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
                yield Label("Enter   View plan details", classes="help-binding")
                yield Label("o       Open PR (or issue if no PR)", classes="help-binding")
                yield Label("p       Open PR in browser", classes="help-binding")
                yield Label("i       Show implement command", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Filter", classes="help-section-title")
                yield Label("/       Start filter mode", classes="help-binding")
                yield Label("Esc     Clear filter / exit filter", classes="help-binding")
                yield Label("Enter   Return focus to table", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("General", classes="help-section-title")
                yield Label("r       Refresh data", classes="help-binding")
                yield Label("?       Show this help", classes="help-binding")
                yield Label("q/Esc   Quit", classes="help-binding")

            yield Label("")
            yield Label("Press any key to close", id="help-footer")


class PlanDetailScreen(ModalScreen):
    """Modal screen showing detailed plan information as an Action Hub."""

    COMMANDS = {PlanCommandProvider}  # Register command provider for palette

    BINDINGS = [
        # Navigation
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        # Links section
        Binding("o", "open_browser", "Open"),
        Binding("i", "open_issue", "Issue"),
        Binding("p", "open_pr", "PR"),
        Binding("r", "open_run", "Run"),
        # Copy section
        Binding("c", "copy_checkout", "Checkout"),
        Binding("e", "copy_pr_checkout", "PR Checkout"),
        Binding("1", "copy_implement", "Implement"),
        Binding("2", "copy_implement_dangerous", "Dangerous"),
        Binding("3", "copy_implement_yolo", "Yolo"),
        Binding("4", "copy_submit", "Submit"),
    ]

    DEFAULT_CSS = """
    PlanDetailScreen {
        align: center middle;
    }

    #detail-dialog {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #detail-header {
        width: 100%;
        height: auto;
    }

    #detail-plan-link {
        text-style: bold;
    }

    #detail-title {
        color: $text;
    }

    .status-badge {
        margin-left: 1;
        padding: 0 1;
    }

    .badge-open {
        background: #238636;
        color: white;
    }

    .badge-closed {
        background: #8957e5;
        color: white;
    }

    .badge-merged {
        background: #8957e5;
        color: white;
    }

    .badge-pr {
        background: $primary;
        color: white;
    }

    .badge-success {
        background: #238636;
        color: white;
    }

    .badge-failure {
        background: #da3633;
        color: white;
    }

    .badge-pending {
        background: #9e6a03;
        color: white;
    }

    .badge-local {
        background: #58a6ff;
        color: black;
        text-style: bold;
    }

    .badge-dim {
        background: $surface-lighten-1;
        color: $text-muted;
    }

    #detail-divider {
        height: 1;
        background: $primary-darken-2;
    }

    .info-row {
        layout: horizontal;
        height: 1;
    }

    .info-label {
        color: $text-muted;
        width: 12;
    }

    .info-value {
        color: $text;
        min-width: 20;
    }

    .copyable-row {
        layout: horizontal;
        height: 1;
    }

    .copyable-text {
        color: $text;
    }

    #detail-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    .log-entry {
        color: $text-muted;
        margin-left: 1;
    }

    .log-section {
        margin-top: 1;
        max-height: 6;
        overflow-y: auto;
    }

    .log-header {
        color: $text-muted;
        text-style: italic;
    }

    .section-header {
        color: $text-muted;
        text-style: bold italic;
        margin-top: 1;
    }

    .command-row {
        layout: horizontal;
        height: 1;
    }

    .command-key {
        color: $accent;
        width: 4;
    }

    .command-text {
        color: $text;
    }
    """

    def __init__(
        self,
        row: PlanRowData,
        clipboard: "Clipboard | None" = None,
        browser: "BrowserLauncher | None" = None,
        executor: CommandExecutor | None = None,
    ) -> None:
        """Initialize with plan row data.

        Args:
            row: PlanRowData containing all plan information
            clipboard: Optional clipboard interface for copy operations
            browser: Optional browser launcher interface for opening URLs
            executor: Optional command executor for palette commands
        """
        super().__init__()
        self._row = row
        self._clipboard = clipboard
        self._browser = browser
        self._executor = executor

    def _get_pr_state_badge(self) -> tuple[str, str]:
        """Get PR state display text and CSS class."""
        state = self._row.pr_state
        if state == "MERGED":
            return ("MERGED", "badge-merged")
        elif state == "CLOSED":
            return ("CLOSED", "badge-closed")
        elif state == "OPEN":
            return ("OPEN", "badge-open")
        return ("PR", "badge-pr")

    def _get_run_badge(self) -> tuple[str, str]:
        """Get workflow run display text and CSS class."""
        if not self._row.run_status:
            return ("No runs", "badge-dim")

        conclusion = self._row.run_conclusion
        if conclusion == "success":
            return ("✓ Passed", "badge-success")
        elif conclusion == "failure":
            return ("✗ Failed", "badge-failure")
        elif conclusion == "cancelled":
            return ("Cancelled", "badge-dim")
        elif self._row.run_status == "in_progress":
            return ("Running...", "badge-pending")
        elif self._row.run_status == "queued":
            return ("Queued", "badge-pending")
        return (self._row.run_status, "badge-dim")

    def action_open_browser(self) -> None:
        """Open the plan (PR if available, otherwise issue) in browser."""
        if self._browser is None:
            return
        if self._row.pr_url:
            self._browser.launch(self._row.pr_url)
        elif self._row.issue_url:
            self._browser.launch(self._row.issue_url)

    def action_open_issue(self) -> None:
        """Open the issue in browser."""
        if self._browser is None:
            return
        if self._row.issue_url:
            self._browser.launch(self._row.issue_url)

    def action_open_pr(self) -> None:
        """Open the PR in browser."""
        if self._browser is None:
            return
        if self._row.pr_url:
            self._browser.launch(self._row.pr_url)

    def action_open_run(self) -> None:
        """Open the workflow run in browser."""
        if self._browser is None:
            return
        if self._row.run_url:
            self._browser.launch(self._row.run_url)

    def _copy_and_notify(self, text: str) -> None:
        """Copy text to clipboard and show notification.

        Args:
            text: Text to copy to clipboard
        """
        if self._clipboard is not None:
            self._clipboard.copy(text)
        # Show brief notification via app's notify method
        self.notify(f"Copied: {text}", timeout=2)

    def action_copy_checkout(self) -> None:
        """Copy local checkout command to clipboard."""
        if self._row.exists_locally:
            cmd = f"erk co {self._row.worktree_name}"
            self._copy_and_notify(cmd)

    def action_copy_pr_checkout(self) -> None:
        """Copy PR checkout command to clipboard."""
        if self._row.pr_number is not None:
            cmd = f"erk pr co {self._row.pr_number}"
            self._copy_and_notify(cmd)

    def action_copy_implement(self) -> None:
        """Copy basic implement command to clipboard."""
        cmd = f"erk implement {self._row.issue_number}"
        self._copy_and_notify(cmd)

    def action_copy_implement_dangerous(self) -> None:
        """Copy implement --dangerous command to clipboard."""
        cmd = f"erk implement {self._row.issue_number} --dangerous"
        self._copy_and_notify(cmd)

    def action_copy_implement_yolo(self) -> None:
        """Copy implement --yolo command to clipboard."""
        cmd = f"erk implement {self._row.issue_number} --yolo"
        self._copy_and_notify(cmd)

    def action_copy_submit(self) -> None:
        """Copy submit command to clipboard."""
        cmd = f"erk submit {self._row.issue_number}"
        self._copy_and_notify(cmd)

    def execute_command(self, command_id: str) -> None:
        """Execute a command from the palette.

        Args:
            command_id: The ID of the command to execute
        """
        if self._executor is None:
            return

        row = self._row
        executor = self._executor

        if command_id == "open_browser":
            url = row.pr_url or row.issue_url
            if url:
                executor.open_url(url)
                executor.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.issue_url:
                executor.open_url(row.issue_url)
                executor.notify(f"Opened issue #{row.issue_number}")

        elif command_id == "open_pr":
            if row.pr_url:
                executor.open_url(row.pr_url)
                executor.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                executor.open_url(row.run_url)
                executor.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            cmd = f"erk co {row.worktree_name}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_pr_checkout":
            cmd = f"erk pr co {row.pr_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement":
            cmd = f"erk implement {row.issue_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_dangerous":
            cmd = f"erk implement {row.issue_number} --dangerous"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_yolo":
            cmd = f"erk implement {row.issue_number} --yolo"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_submit":
            cmd = f"erk submit {row.issue_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "close_plan":
            if row.issue_url:
                closed_prs = executor.close_plan(row.issue_number, row.issue_url)
                if closed_prs:
                    pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
                    executor.notify(f"Closed plan #{row.issue_number} and PRs: {pr_list}")
                else:
                    executor.notify(f"Closed plan #{row.issue_number}")
                executor.refresh_data()
                # Close modal after closing plan (only when running in app context)
                if self.is_attached:
                    self.dismiss()

        elif command_id == "submit_to_queue":
            if row.issue_url:
                executor.notify(f"Submitting plan #{row.issue_number} to queue...")
                executor.submit_to_queue(row.issue_number, row.issue_url)
                executor.notify(f"Submitted plan #{row.issue_number} to queue")
                executor.refresh_data()
                # Close modal after submission (only when running in app context)
                if self.is_attached:
                    self.dismiss()

    def compose(self) -> ComposeResult:
        """Create detail dialog content as an Action Hub."""
        with Vertical(id="detail-dialog"):
            # Header: Plan number + title
            with Vertical(id="detail-header"):
                plan_text = f"Plan #{self._row.issue_number}"
                yield Label(plan_text, id="detail-plan-link")
                yield Label(self._row.full_title, id="detail-title", markup=False)

            # Divider
            yield Label("", id="detail-divider")

            # ISSUE/PR INFO SECTION
            # Issue Info - clickable issue number
            with Container(classes="info-row"):
                yield Label("Issue", classes="info-label")
                if self._row.issue_url:
                    yield ClickableLink(
                        f"#{self._row.issue_number}", self._row.issue_url, classes="info-value"
                    )
                else:
                    yield Label(f"#{self._row.issue_number}", classes="info-value", markup=False)

            # PR Info (if exists) - clickable PR number with state badge inline
            if self._row.pr_number:
                with Container(classes="info-row"):
                    yield Label("PR", classes="info-label")
                    if self._row.pr_url:
                        yield ClickableLink(
                            f"#{self._row.pr_number}", self._row.pr_url, classes="info-value"
                        )
                    else:
                        yield Label(f"#{self._row.pr_number}", classes="info-value", markup=False)
                    # PR state badge inline
                    pr_text, pr_class = self._get_pr_state_badge()
                    yield Label(pr_text, classes=f"status-badge {pr_class}")

                # PR title if different from issue title
                if self._row.pr_title and self._row.pr_title != self._row.full_title:
                    with Container(classes="info-row"):
                        yield Label("PR Title", classes="info-label")
                        yield Label(self._row.pr_title, classes="info-value", markup=False)

                # Checks status
                if self._row.checks_display and self._row.checks_display != "-":
                    with Container(classes="info-row"):
                        yield Label("Checks", classes="info-label")
                        yield Label(self._row.checks_display, classes="info-value", markup=False)

            # REMOTE RUN INFO SECTION (separate from worktree/local info)
            if self._row.run_id:
                with Container(classes="info-row"):
                    yield Label("Run", classes="info-label")
                    if self._row.run_url:
                        yield ClickableLink(
                            self._row.run_id, self._row.run_url, classes="info-value"
                        )
                    else:
                        yield Label(self._row.run_id, classes="info-value", markup=False)
                    # Run status badge inline
                    run_text, run_class = self._get_run_badge()
                    yield Label(run_text, classes=f"status-badge {run_class}")

                if self._row.remote_impl_display and self._row.remote_impl_display != "-":
                    with Container(classes="info-row"):
                        yield Label("Last remote impl", classes="info-label")
                        yield Label(
                            self._row.remote_impl_display, classes="info-value", markup=False
                        )

            # COMMANDS SECTION (copy to clipboard)
            # All items below use uniform orange labels that copy when clicked
            yield Label("COMMANDS (copy)", classes="section-header")

            # PR checkout command (if PR exists)
            if self._row.pr_number is not None:
                pr_checkout_cmd = f"erk pr co {self._row.pr_number}"
                with Container(classes="command-row"):
                    yield CopyableLabel(pr_checkout_cmd, pr_checkout_cmd)

            # Implement commands
            implement_cmd = f"erk implement {self._row.issue_number}"
            with Container(classes="command-row"):
                yield Label("[1]", classes="command-key")
                yield CopyableLabel(implement_cmd, implement_cmd)

            dangerous_cmd = f"erk implement {self._row.issue_number} --dangerous"
            with Container(classes="command-row"):
                yield Label("[2]", classes="command-key")
                yield CopyableLabel(dangerous_cmd, dangerous_cmd)

            yolo_cmd = f"erk implement {self._row.issue_number} --yolo"
            with Container(classes="command-row"):
                yield Label("[3]", classes="command-key")
                yield CopyableLabel(yolo_cmd, yolo_cmd)

            # Submit command
            submit_cmd = f"erk submit {self._row.issue_number}"
            with Container(classes="command-row"):
                yield Label("[4]", classes="command-key")
                yield CopyableLabel(submit_cmd, submit_cmd)

            # Log entries (if any) - clickable timestamps
            if self._row.log_entries:
                with Vertical(classes="log-section"):
                    yield Label("Recent activity", classes="log-header")
                    for event_name, timestamp, comment_url in self._row.log_entries[:5]:
                        log_text = f"{timestamp}  {event_name}"
                        if comment_url:
                            yield ClickableLink(log_text, comment_url, classes="log-entry")
                        else:
                            yield Label(log_text, classes="log-entry", markup=False)

            yield Label("Ctrl+P: commands  Esc: close", id="detail-footer")


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
        Binding("enter", "show_detail", "Detail"),
        Binding("o", "open_row", "Open", show=False),
        Binding("p", "open_pr", "Open PR"),
        # NOTE: 'c' binding removed - close_plan now accessible via command palette
        # in the plan detail modal (Enter → Ctrl+P → "Close Plan")
        Binding("i", "show_implement", "Implement"),
        Binding("slash", "start_filter", "Filter", key_display="/"),
    ]

    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        """Return system commands, hiding them on modal screens.

        Hides Keys, Quit, Screenshot, Theme from command palette when on
        PlanDetailScreen modal so only plan-specific commands appear.
        """
        if isinstance(screen, PlanDetailScreen):
            return iter(())
        yield from super().get_system_commands(screen)

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
        self._filter_input: Input | None = None
        self._all_rows: list[PlanRowData] = []  # Unfiltered data
        self._rows: list[PlanRowData] = []  # Currently displayed (possibly filtered)
        self._refresh_task: asyncio.Task | None = None
        self._loading = True
        self._filter_state = FilterState.initial()

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Label("Loading plans...", id="loading-message")
            yield PlanDataTable(self._plan_filters)
        yield Input(id="filter-input", placeholder="Filter...", disabled=True)
        yield StatusBar()

    def on_mount(self) -> None:
        """Initialize app after mounting."""
        self._table = self.query_one(PlanDataTable)
        self._status_bar = self.query_one(StatusBar)
        self._filter_input = self.query_one("#filter-input", Input)
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
        self._all_rows = rows
        self._loading = False

        # Apply current filter if active
        if self._filter_state.mode == FilterMode.ACTIVE and self._filter_state.query:
            self._rows = filter_plans(rows, self._filter_state.query)
        else:
            self._rows = rows

        if self._table is not None:
            self._loading_label.display = False
            self._table.display = True
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))
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
        """Quit the application or handle progressive escape from filter mode."""
        if self._filter_state.mode == FilterMode.ACTIVE:
            self._filter_state = self._filter_state.handle_escape()
            if self._filter_state.mode == FilterMode.INACTIVE:
                # Fully exited filter mode
                self._exit_filter_mode()
            else:
                # Just cleared text, stay in filter mode
                if self._filter_input is not None:
                    self._filter_input.value = ""
                # Reset to show all rows
                self._apply_filter()
            return
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

    def action_show_detail(self) -> None:
        """Show plan detail modal for selected row."""
        row = self._get_selected_row()
        if row is None:
            return

        # Create executor with injected dependencies
        executor = RealCommandExecutor(
            browser_launch=self._provider.browser.launch,
            clipboard_copy=self._provider.clipboard.copy,
            close_plan_fn=self._provider.close_plan,
            notify_fn=self.notify,
            refresh_fn=self.action_refresh,
            submit_to_queue_fn=self._provider.submit_to_queue,
        )

        self.push_screen(
            PlanDetailScreen(
                row,
                clipboard=self._provider.clipboard,
                browser=self._provider.browser,
                executor=executor,
            )
        )

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j key)."""
        if self._table is not None:
            self._table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k key)."""
        if self._table is not None:
            self._table.action_cursor_up()

    def action_start_filter(self) -> None:
        """Activate filter mode and focus the input."""
        if self._filter_input is None:
            return
        self._filter_state = self._filter_state.activate()
        self._filter_input.disabled = False
        self._filter_input.add_class("visible")
        self._filter_input.focus()

    def _apply_filter(self) -> None:
        """Apply current filter query to the table."""
        if self._filter_state.query:
            self._rows = filter_plans(self._all_rows, self._filter_state.query)
        else:
            self._rows = self._all_rows

        if self._table is not None:
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))

    def _exit_filter_mode(self) -> None:
        """Exit filter mode, restore all rows, and focus table."""
        if self._filter_input is not None:
            self._filter_input.value = ""
            self._filter_input.remove_class("visible")
            self._filter_input.disabled = True

        self._filter_state = FilterState.initial()
        self._rows = self._all_rows

        if self._table is not None:
            self._table.populate(self._rows)
            self._table.focus()

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))

    def action_open_row(self) -> None:
        """Open selected row - PR if available, otherwise issue."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        elif row.issue_url:
            self._provider.browser.launch(row.issue_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened issue #{row.issue_number}")

    def action_open_pr(self) -> None:
        """Open selected PR in browser."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
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

    def action_close_plan(self) -> None:
        """Close the selected plan and its linked PRs."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.issue_url is None:
            if self._status_bar is not None:
                self._status_bar.set_message("Cannot close plan: no issue URL")
            return

        # Perform the close operation
        closed_prs = self._provider.close_plan(row.issue_number, row.issue_url)

        # Show status message
        if self._status_bar is not None:
            if closed_prs:
                pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
                self._status_bar.set_message(f"Closed plan #{row.issue_number} and PRs: {pr_list}")
            else:
                self._status_bar.set_message(f"Closed plan #{row.issue_number}")

        # Refresh data to remove the closed plan from the list
        self.action_refresh()

    def _copy_checkout_command(self, row: PlanRowData) -> None:
        """Copy appropriate checkout command based on row state.

        If worktree exists locally, copies 'erk co {worktree_name}'.
        If only PR available, copies 'erk pr co {pr_number}'.
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
            cmd = f"erk pr co {row.pr_number}"
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
        """Handle Enter/double-click on row - show plan details."""
        self.action_show_detail()

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        """Handle filter input text changes."""
        self._filter_state = self._filter_state.with_query(event.value)
        self._apply_filter()

    @on(Input.Submitted, "#filter-input")
    def on_filter_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in filter input - return focus to table."""
        if self._table is not None:
            self._table.focus()

    @on(PlanDataTable.PlanClicked)
    def on_plan_clicked(self, event: PlanDataTable.PlanClicked) -> None:
        """Handle click on plan cell - open issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.issue_url:
                self._provider.browser.launch(row.issue_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened issue #{row.issue_number}")

    @on(PlanDataTable.PrClicked)
    def on_pr_clicked(self, event: PlanDataTable.PrClicked) -> None:
        """Handle click on pr cell - open PR in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened PR #{row.pr_number}")

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
                self._provider.browser.launch(row.run_url)
                if self._status_bar is not None:
                    # Extract run ID from URL to avoid Rich markup in status bar
                    run_id = row.run_url.rsplit("/", 1)[-1]
                    self._status_bar.set_message(f"Opened run {run_id}")
