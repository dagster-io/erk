"""Main Textual application for erk dash interactive mode."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Input, Label

from erk.tui.commands.provider import MainListCommandProvider
from erk.tui.commands.real_executor import RealCommandExecutor
from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.filtering.logic import filter_plans
from erk.tui.filtering.types import FilterMode, FilterState
from erk.tui.screens.help_screen import HelpScreen
from erk.tui.screens.issue_body_screen import IssueBodyScreen
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import BranchActivity, SortKey, SortState
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar


class ErkDashApp(App):
    """Interactive TUI for erk dash command.

    Displays plans in a navigable table with quick actions.
    """

    CSS_PATH = Path(__file__).parent / "styles" / "dash.tcss"
    COMMANDS = {MainListCommandProvider}

    BINDINGS = [
        Binding("q", "exit_app", "Quit"),
        Binding("escape", "exit_app", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "show_detail", "Detail"),
        Binding("space", "show_detail", "Detail", show=False),
        Binding("o", "open_row", "Open", show=False),
        Binding("p", "open_pr", "Open PR"),
        # NOTE: 'c' binding removed - close_plan now accessible via command palette
        # in the plan detail modal (Enter → Ctrl+P → "Close Plan")
        Binding("i", "show_implement", "Implement"),
        Binding("v", "view_issue_body", "View", show=False),
        Binding("slash", "start_filter", "Filter", key_display="/"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("ctrl+p", "command_palette", "Commands"),
    ]

    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        """Return system commands, hiding them when plan commands are available.

        Hides Keys, Quit, Screenshot, Theme from command palette when on
        PlanDetailScreen or when main list has a selected row, so only
        plan-specific commands appear.
        """
        if isinstance(screen, PlanDetailScreen):
            return iter(())
        # Hide system commands on main list when a row is selected
        if self._get_selected_row() is not None:
            return iter(())
        yield from super().get_system_commands(screen)

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        filters: PlanFilters,
        refresh_interval: float = 15.0,
        initial_sort: SortState | None = None,
    ) -> None:
        """Initialize the dashboard app.

        Args:
            provider: Data provider for fetching plan data
            filters: Filter options for the plan list
            refresh_interval: Seconds between auto-refresh (0 to disable)
            initial_sort: Initial sort state (defaults to by issue number)
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
        self._sort_state = initial_sort if initial_sort is not None else SortState.initial()
        self._activity_by_issue: dict[int, BranchActivity] = {}
        self._activity_loading = False

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

        try:
            # Run sync fetch in executor to avoid blocking
            loop = asyncio.get_running_loop()
            rows = await loop.run_in_executor(None, self._provider.fetch_plans, self._plan_filters)

            # If sorting by activity, also fetch activity data
            if self._sort_state.key == SortKey.BRANCH_ACTIVITY:
                activity = await loop.run_in_executor(
                    None, self._provider.fetch_branch_activity, rows
                )
                self._activity_by_issue = activity

        except Exception as e:
            # GitHub API failure, network error, etc.
            self.notify(f"Failed to load plans: {e}", severity="error", timeout=5)
            rows = []

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

        # Apply filter and sort
        self._rows = self._apply_filter_and_sort(rows)

        if self._table is not None:
            self._loading_label.display = False
            self._table.display = True
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))
            self._status_bar.set_sort_mode(self._sort_state.display_label)
            if update_time is not None:
                self._status_bar.set_last_update(update_time, duration)

    def _apply_filter_and_sort(self, rows: list[PlanRowData]) -> list[PlanRowData]:
        """Apply current filter and sort to rows.

        Args:
            rows: Raw rows to process

        Returns:
            Filtered and sorted rows
        """
        # Apply filter first
        if self._filter_state.mode == FilterMode.ACTIVE and self._filter_state.query:
            filtered = filter_plans(rows, self._filter_state.query)
        else:
            filtered = rows

        # Apply sort
        return sort_plans(
            filtered,
            self._sort_state.key,
            self._activity_by_issue if self._sort_state.key == SortKey.BRANCH_ACTIVITY else None,
        )

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

    def action_toggle_sort(self) -> None:
        """Toggle between sort modes."""
        self._sort_state = self._sort_state.toggle()

        # If switching to activity sort, load activity data in background
        if self._sort_state.key == SortKey.BRANCH_ACTIVITY and not self._activity_by_issue:
            self._load_activity_and_resort()
        else:
            # Re-sort with current data
            self._rows = self._apply_filter_and_sort(self._all_rows)
            if self._table is not None:
                self._table.populate(self._rows)

        # Update status bar
        if self._status_bar is not None:
            self._status_bar.set_sort_mode(self._sort_state.display_label)

    @work(thread=True)
    def _load_activity_and_resort(self) -> None:
        """Load branch activity in background, then resort."""
        self._activity_loading = True

        # Fetch activity data
        activity = self._provider.fetch_branch_activity(self._all_rows)

        # Update on main thread
        self.app.call_from_thread(self._on_activity_loaded, activity)

    def _on_activity_loaded(self, activity: dict[int, BranchActivity]) -> None:
        """Handle activity data loaded - resort the table."""
        self._activity_by_issue = activity
        self._activity_loading = False

        # Re-sort with new activity data
        self._rows = self._apply_filter_and_sort(self._all_rows)
        if self._table is not None:
            self._table.populate(self._rows)

    @work(thread=True)
    def _close_plan_async(self, issue_number: int, issue_url: str) -> None:
        """Close plan in background thread with toast notifications.

        Args:
            issue_number: The plan issue number
            issue_url: The GitHub issue URL
        """
        # Error boundary: catch all exceptions from the close operation to display
        # them as toast notifications rather than crashing the TUI.
        try:
            closed_prs = self._provider.close_plan(issue_number, issue_url)
            # Success toast
            if closed_prs:
                msg = f"Closed plan #{issue_number} (and {len(closed_prs)} linked PRs)"
            else:
                msg = f"Closed plan #{issue_number}"
            self.call_from_thread(self.notify, msg, timeout=3)
            # Trigger data refresh
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            # Error toast
            self.call_from_thread(
                self.notify,
                f"Failed to close plan #{issue_number}: {e}",
                severity="error",
                timeout=5,
            )

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
                row=row,
                clipboard=self._provider.clipboard,
                browser=self._provider.browser,
                executor=executor,
                repo_root=self._provider.repo_root,
            )
        )

    def action_view_issue_body(self) -> None:
        """Display the plan content in a modal (fetched on-demand)."""
        row = self._get_selected_row()
        if row is None:
            return
        # Push screen that will fetch plan content on-demand
        self.push_screen(
            IssueBodyScreen(
                provider=self._provider,
                issue_number=row.issue_number,
                issue_body=row.issue_body,
                full_title=row.full_title,
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
        self._rows = self._apply_filter_and_sort(self._all_rows)

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
        self._rows = self._apply_filter_and_sort(self._all_rows)

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
        """Close the selected plan and its linked PRs (async with toast)."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.issue_url is None:
            self.notify("Cannot close plan: no issue URL", severity="warning")
            return

        # Show starting toast and run async - no blocking
        self.notify(f"Closing plan #{row.issue_number}...")
        self._close_plan_async(row.issue_number, row.issue_url)

    def _copy_checkout_command(self, row: PlanRowData) -> None:
        """Copy appropriate checkout command based on row state.

        If worktree exists locally, copies 'erk co {worktree_name}'.
        If only PR available, copies 'erk pr co {pr_number}'.
        Shows status message with result.

        Args:
            row: The plan row data to generate command from
        """
        # Determine which command to use
        if row.worktree_branch is not None:
            # Local worktree exists - use branch checkout
            cmd = f"erk br co {row.worktree_branch}"
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

    def execute_palette_command(self, command_id: str) -> None:
        """Execute a command from the palette on the selected row.

        Args:
            command_id: The ID of the command to execute
        """
        row = self._get_selected_row()
        if row is None:
            return

        if command_id == "open_browser":
            url = row.pr_url or row.issue_url
            if url:
                self._provider.browser.launch(url)
                self.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.issue_url:
                self._provider.browser.launch(row.issue_url)
                self.notify(f"Opened issue #{row.issue_number}")

        elif command_id == "open_pr":
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)
                self.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                self._provider.browser.launch(row.run_url)
                self.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            cmd = f"erk br co {row.worktree_branch}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_pr_checkout":
            cmd = f"erk pr checkout {row.pr_number} && erk pr sync --dangerous"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement":
            cmd = f"erk implement {row.issue_number}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_dangerous":
            cmd = f"erk implement {row.issue_number} --dangerous"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_yolo":
            cmd = f"erk implement {row.issue_number} --yolo"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_submit":
            cmd = f"erk plan submit {row.issue_number}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "close_plan":
            if row.issue_url:
                # Show starting toast and run async - no modal blocking
                self.notify(f"Closing plan #{row.issue_number}...")
                self._close_plan_async(row.issue_number, row.issue_url)

        elif command_id == "submit_to_queue":
            if row.issue_url:
                # Open detail modal to show streaming output
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self.notify,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                )
                detail_screen = PlanDetailScreen(
                    row=row,
                    clipboard=self._provider.clipboard,
                    browser=self._provider.browser,
                    executor=executor,
                    repo_root=self._provider.repo_root,
                )
                self.push_screen(detail_screen)
                # Trigger the streaming command after screen is mounted
                detail_screen.call_after_refresh(
                    lambda: detail_screen.run_streaming_command(
                        ["erk", "plan", "submit", str(row.issue_number)],
                        cwd=self._provider.repo_root,
                        title=f"Submitting Plan #{row.issue_number}",
                    )
                )

        elif command_id == "land_pr":
            if row.pr_number:
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self.notify,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                )
                detail_screen = PlanDetailScreen(
                    row=row,
                    clipboard=self._provider.clipboard,
                    browser=self._provider.browser,
                    executor=executor,
                    repo_root=self._provider.repo_root,
                )
                self.push_screen(detail_screen)
                detail_screen.call_after_refresh(
                    lambda: detail_screen.run_streaming_command(
                        ["erk", "land", str(row.pr_number), "-f", "--script"],
                        cwd=self._provider.repo_root,
                        title=f"Landing PR #{row.pr_number}",
                    )
                )

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
        """Handle click on local-wt cell - copy worktree name to clipboard."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.worktree_name:
                success = self._provider.clipboard.copy(row.worktree_name)
                if success:
                    self.notify(f"Copied: {row.worktree_name}", timeout=2)
                else:
                    self.notify("Clipboard unavailable", severity="error", timeout=2)

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
