"""Main Textual application for erk dash interactive mode."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Input, Label

from erk.tui.commands.provider import MainListCommandProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.filtering.logic import filter_plans
from erk.tui.filtering.types import FilterMode, FilterState
from erk.tui.screens.help_screen import HelpScreen
from erk.tui.screens.plan_body_screen import PlanBodyScreen
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import BranchActivity, SortKey, SortState
from erk.tui.views.types import (
    ViewMode,
    get_next_view_mode,
    get_previous_view_mode,
    get_view_config,
)
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk.tui.widgets.view_bar import ViewBar
from erk_shared.gateway.command_executor.real import RealCommandExecutor
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _build_github_url(plan_url: str, resource_type: str, number: int) -> str:
    """Build a GitHub URL for a PR or issue from an existing plan URL.

    Args:
        plan_url: Base plan URL (e.g., https://github.com/owner/repo/issues/123)
        resource_type: Either "pull" or "issues"
        number: The PR or issue number

    Returns:
        Full URL (e.g., https://github.com/owner/repo/pull/456)
    """
    base_url = plan_url.rsplit("/issues/", 1)[0]
    return f"{base_url}/{resource_type}/{number}"


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
        Binding("c", "view_comments", "Comments", show=False),
        Binding("i", "show_implement", "Implement"),
        Binding("v", "view_plan_body", "View", show=False),
        Binding("slash", "start_filter", "Filter", key_display="/"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("1", "switch_view_plans", "Plans", show=False),
        Binding("2", "switch_view_learn", "Learn", show=False),
        Binding("3", "switch_view_objectives", "Objectives", show=False),
        Binding("right", "next_view", "Next View", show=False, priority=True),
        Binding("left", "previous_view", "Previous View", show=False, priority=True),
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
        self._activity_by_plan: dict[int, BranchActivity] = {}
        self._activity_loading = False
        self._view_mode: ViewMode = ViewMode.PLANS
        self._view_bar: ViewBar | None = None
        self._data_cache: dict[tuple[str, ...], list[PlanRowData]] = {}

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        yield ViewBar(active_view=self._view_mode)
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
        self._view_bar = self.query_one(ViewBar)

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

        # Snapshot view mode at fetch start to avoid race conditions.
        # If the user switches tabs during the fetch, self._view_mode changes
        # but fetched_mode retains the original value so results are cached
        # under the correct key and stale results don't overwrite the display.
        fetched_mode = self._view_mode
        view_config = get_view_config(fetched_mode)
        active_filters = PlanFilters(
            labels=view_config.labels,
            state=self._plan_filters.state,
            run_state=self._plan_filters.run_state,
            limit=self._plan_filters.limit,
            show_prs=self._plan_filters.show_prs,
            show_runs=self._plan_filters.show_runs,
            creator=self._plan_filters.creator,
        )

        try:
            # Run sync fetch in executor to avoid blocking
            loop = asyncio.get_running_loop()
            rows = await loop.run_in_executor(None, self._provider.fetch_plans, active_filters)

            # If sorting by activity, also fetch activity data
            if self._sort_state.key == SortKey.BRANCH_ACTIVITY:
                activity = await loop.run_in_executor(
                    None, self._provider.fetch_branch_activity, rows
                )
                self._activity_by_plan = activity

        except Exception as e:
            # GitHub API failure, network error, etc.
            self.notify(f"Failed to load plans: {e}", severity="error", timeout=5)
            rows = []

        # Calculate duration
        duration = time.monotonic() - start_time
        update_time = datetime.now().strftime("%H:%M:%S")

        # Update UI directly since we're in async context
        self._update_table(rows, update_time, duration, fetched_mode=fetched_mode)

    def _update_table(
        self,
        rows: list[PlanRowData],
        update_time: str | None,
        duration: float | None,
        *,
        fetched_mode: ViewMode,
    ) -> None:
        """Update table with new data.

        Args:
            rows: Plan data to display
            update_time: Formatted time of this update
            duration: Duration of the fetch in seconds
            fetched_mode: The view mode that was active when the fetch started.
                Data is cached under that mode's labels and the display is only
                updated if it still matches the current view.
        """
        # Cache under the FETCHED view's labels (always correct)
        fetched_config = get_view_config(fetched_mode)
        self._data_cache[fetched_config.labels] = rows

        # If user switched tabs during fetch, don't touch the display
        if fetched_mode != self._view_mode:
            return

        rows = self._filter_rows_for_view(rows, self._view_mode)

        self._all_rows = rows
        self._loading = False

        # Apply filter and sort
        self._rows = self._apply_filter_and_sort(rows)

        if self._table is not None:
            self._loading_label.display = False
            self._table.display = True
            self._table.populate(self._rows)

        if self._status_bar is not None:
            current_config = get_view_config(self._view_mode)
            noun = current_config.display_name.lower()
            self._status_bar.set_plan_count(len(self._rows), noun=noun)
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
            self._activity_by_plan if self._sort_state.key == SortKey.BRANCH_ACTIVITY else None,
        )

    @staticmethod
    def _filter_rows_for_view(rows: list[PlanRowData], mode: ViewMode) -> list[PlanRowData]:
        """Filter rows based on view mode.

        Plans view excludes learn plans; Learn view includes only learn plans.

        Args:
            rows: Raw rows to filter
            mode: The active view mode

        Returns:
            Filtered rows for the given view
        """
        if mode == ViewMode.LEARN:
            return [r for r in rows if r.is_learn_plan]
        if mode == ViewMode.PLANS:
            return [r for r in rows if not r.is_learn_plan]
        return rows

    def _notify_with_severity(self, message: str, severity: str | None) -> None:
        """Wrapper for notify that handles optional severity.

        Args:
            message: The notification message
            severity: Optional severity level, uses default if None
        """
        if severity is None:
            self.notify(message)
        else:
            # Ensure severity is one of the valid values expected by Textual
            from textual.app import SeverityLevel

            if severity in ("information", "warning", "error"):
                valid_severity: SeverityLevel = severity  # type: ignore[assignment]
                self.notify(message, severity=valid_severity)
            else:
                # Fallback to default severity for unknown values
                self.notify(message)

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

    def _switch_view(self, mode: ViewMode) -> None:
        """Switch to a different view mode.

        Caches current data, reconfigures the table, and loads new data.

        Args:
            mode: The view mode to switch to
        """
        if mode == self._view_mode:
            return

        self._view_mode = mode
        view_config = get_view_config(mode)

        # Update view bar
        if self._view_bar is not None:
            self._view_bar.set_active_view(mode)

        # Reconfigure table columns for the new view
        if self._table is not None:
            self._table.reconfigure(
                plan_filters=self._plan_filters,
                view_mode=mode,
            )

        # Check cache for the new view's labels
        cached_data = self._data_cache.get(view_config.labels)
        if cached_data is not None:
            rows = self._filter_rows_for_view(cached_data, mode)
            self._all_rows = rows
            self._rows = self._apply_filter_and_sort(rows)
            if self._table is not None:
                self._table.populate(self._rows)
            if self._status_bar is not None:
                noun = view_config.display_name.lower()
                self._status_bar.set_plan_count(len(self._rows), noun=noun)
        else:
            # No cached data - fetch fresh
            self.run_worker(self._load_data(), exclusive=True)

    def action_switch_view_plans(self) -> None:
        """Switch to Plans view."""
        self._switch_view(ViewMode.PLANS)

    def action_switch_view_learn(self) -> None:
        """Switch to Learn view."""
        self._switch_view(ViewMode.LEARN)

    def action_switch_view_objectives(self) -> None:
        """Switch to Objectives view."""
        self._switch_view(ViewMode.OBJECTIVES)

    def action_next_view(self) -> None:
        """Cycle to the next view (right arrow)."""
        self._switch_view(get_next_view_mode(self._view_mode))

    def action_previous_view(self) -> None:
        """Cycle to the previous view (left arrow)."""
        self._switch_view(get_previous_view_mode(self._view_mode))

    def action_toggle_sort(self) -> None:
        """Toggle between sort modes."""
        self._sort_state = self._sort_state.toggle()

        # If switching to activity sort, load activity data in background
        if self._sort_state.key == SortKey.BRANCH_ACTIVITY and not self._activity_by_plan:
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
        self._activity_by_plan = activity
        self._activity_loading = False

        # Re-sort with new activity data
        self._rows = self._apply_filter_and_sort(self._all_rows)
        if self._table is not None:
            self._table.populate(self._rows)

    @work(thread=True)
    def _close_plan_async(self, plan_id: int, plan_url: str) -> None:
        """Close plan in background thread with toast notifications.

        Args:
            plan_id: The plan identifier
            plan_url: The plan URL
        """
        # Error boundary: catch all exceptions from the close operation to display
        # them as toast notifications rather than crashing the TUI.
        try:
            closed_prs = self._provider.close_plan(plan_id, plan_url)
            # Success toast
            if closed_prs:
                msg = f"Closed plan #{plan_id} (and {len(closed_prs)} linked PRs)"
            else:
                msg = f"Closed plan #{plan_id}"
            self.call_from_thread(self.notify, msg, timeout=3)
            # Trigger data refresh
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            # Error toast
            self.call_from_thread(
                self.notify,
                f"Failed to close plan #{plan_id}: {e}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _update_objective_async(
        self,
        *,
        objective_issue: int,
        pr_num: int,
        branch: str,
    ) -> None:
        """Update objective after landing a PR in background thread.

        Args:
            objective_issue: The objective issue number to update
            pr_num: The PR number that was landed
            branch: The PR head branch name
        """
        self.call_from_thread(self.notify, f"Updating objective #{objective_issue}...")
        try:
            self._provider.update_objective_after_land(
                objective_issue=objective_issue,
                pr_num=pr_num,
                branch=branch,
            )
            self.call_from_thread(self.notify, f"Objective #{objective_issue} updated", timeout=5)
        except Exception:
            self.call_from_thread(
                self.notify,
                "Objective update failed",
                severity="error",
                timeout=8,
            )

    def _push_streaming_detail(
        self,
        *,
        row: PlanRowData,
        command: list[str],
        title: str,
        timeout: float,
        on_success: Callable[[], None] | None,
    ) -> None:
        """Push a detail screen and run a streaming command after refresh."""
        executor = RealCommandExecutor(
            browser_launch=self._provider.browser.launch,
            clipboard_copy=self._provider.clipboard.copy,
            close_plan_fn=self._provider.close_plan,
            notify_fn=self._notify_with_severity,
            refresh_fn=self.action_refresh,
            submit_to_queue_fn=self._provider.submit_to_queue,
            update_objective_fn=lambda oi, pn, br: self._update_objective_async(
                objective_issue=oi,
                pr_num=pn,
                branch=br,
            ),
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
                command,
                cwd=self._provider.repo_root,
                title=title,
                timeout=timeout,
                on_success=on_success,
            )
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
            notify_fn=self._notify_with_severity,
            refresh_fn=self.action_refresh,
            submit_to_queue_fn=self._provider.submit_to_queue,
            update_objective_fn=lambda oi, pn, br: self._update_objective_async(
                objective_issue=oi,
                pr_num=pn,
                branch=br,
            ),
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

    def action_view_plan_body(self) -> None:
        """Display the plan/objective content in a modal (fetched on-demand)."""
        row = self._get_selected_row()
        if row is None:
            return
        content_type = "Objective" if self._view_mode == ViewMode.OBJECTIVES else "Plan"
        # Push screen that will fetch content on-demand
        self.push_screen(
            PlanBodyScreen(
                provider=self._provider,
                plan_id=row.plan_id,
                plan_body=row.plan_body,
                full_title=row.full_title,
                content_type=content_type,
            )
        )

    def action_view_comments(self) -> None:
        """Display unresolved PR review comments in a modal."""
        row = self._get_selected_row()
        if row is None:
            return
        if row.pr_number is None:
            if self._status_bar is not None:
                self._status_bar.set_message("No PR linked to this plan")
            return
        unresolved = row.total_comment_count - row.resolved_comment_count
        if unresolved == 0:
            if self._status_bar is not None:
                self._status_bar.set_message("No unresolved comments")
            return
        self.push_screen(
            UnresolvedCommentsScreen(
                provider=self._provider,
                pr_number=row.pr_number,
                full_title=row.full_title,
                resolved_count=row.resolved_comment_count,
                total_count=row.total_comment_count,
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
            view_config = get_view_config(self._view_mode)
            self._status_bar.set_plan_count(len(self._rows), noun=view_config.display_name.lower())

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
            view_config = get_view_config(self._view_mode)
            self._status_bar.set_plan_count(len(self._rows), noun=view_config.display_name.lower())

    def action_open_row(self) -> None:
        """Open selected row - PR if available, otherwise issue."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        elif row.plan_url:
            self._provider.browser.launch(row.plan_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened issue #{row.plan_id}")

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

        cmd = f"erk implement {row.plan_id}"
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

        if row.plan_url is None:
            self.notify("Cannot close plan: no issue URL", severity="warning")
            return

        # Show starting toast and run async - no blocking
        self.notify(f"Closing plan #{row.plan_id}...")
        self._close_plan_async(row.plan_id, row.plan_url)

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
            url = row.pr_url or row.plan_url
            if url:
                self._provider.browser.launch(url)
                self.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.plan_url:
                self._provider.browser.launch(row.plan_url)
                self.notify(f"Opened issue #{row.plan_id}")

        elif command_id == "open_pr":
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)
                self.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                self._provider.browser.launch(row.run_url)
                self.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            self._copy_checkout_command(row)

        elif command_id == "copy_pr_checkout":
            cmd = f'source "$(erk pr checkout {row.pr_number} --script)" && erk pr sync --dangerous'
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_prepare":
            cmd = f"erk prepare {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_prepare_activate":
            cmd = f'source "$(erk prepare {row.plan_id} --script)" && erk implement --dangerous'
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_submit":
            cmd = f"erk plan submit {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_replan":
            cmd = f"erk plan replan {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "fix_conflicts_remote":
            if row.pr_number:
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self._notify_with_severity,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                    update_objective_fn=lambda oi, pn, br: self._update_objective_async(
                        objective_issue=oi,
                        pr_num=pn,
                        branch=br,
                    ),
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
                        [
                            "erk",
                            "launch",
                            "pr-fix-conflicts",
                            "--pr",
                            str(row.pr_number),
                        ],
                        cwd=self._provider.repo_root,
                        title=f"Fix Conflicts Remote PR #{row.pr_number}",
                    )
                )

        elif command_id == "address_remote":
            if row.pr_number:
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self._notify_with_severity,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                    update_objective_fn=lambda oi, pn, br: self._update_objective_async(
                        objective_issue=oi,
                        pr_num=pn,
                        branch=br,
                    ),
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
                        ["erk", "launch", "pr-address", "--pr", str(row.pr_number)],
                        cwd=self._provider.repo_root,
                        title=f"Address Remote PR #{row.pr_number}",
                    )
                )

        elif command_id == "close_plan":
            if row.plan_url:
                # Show starting toast and run async - no modal blocking
                self.notify(f"Closing plan #{row.plan_id}...")
                self._close_plan_async(row.plan_id, row.plan_url)

        elif command_id == "submit_to_queue":
            if row.plan_url:
                self._push_streaming_detail(
                    row=row,
                    command=["erk", "plan", "submit", str(row.plan_id), "-f"],
                    title=f"Submit Plan #{row.plan_id}",
                    timeout=30.0,
                    on_success=self.action_refresh,
                )

        elif command_id == "land_pr":
            if row.pr_number and row.pr_head_branch:
                pr_num = row.pr_number
                branch = row.pr_head_branch
                objective_issue = row.objective_issue

                def _on_land_success() -> None:
                    self.action_refresh()
                    if objective_issue is not None:
                        self._update_objective_async(
                            objective_issue=objective_issue,
                            pr_num=pr_num,
                            branch=branch,
                        )

                self._push_streaming_detail(
                    row=row,
                    command=[
                        "erk",
                        "exec",
                        "land-execute",
                        f"--pr-number={pr_num}",
                        f"--branch={branch}",
                        "-f",
                    ],
                    title=f"Land PR #{pr_num}",
                    timeout=600.0,
                    on_success=_on_land_success,
                )

        elif command_id == "copy_replan":
            cmd = f"/erk:replan {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        # === OBJECTIVE COMMANDS ===
        elif command_id == "copy_plan":
            cmd = f"erk objective plan {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_view":
            cmd = f"erk objective view {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "open_objective":
            if row.plan_url:
                self._provider.browser.launch(row.plan_url)
                self.notify(f"Opened objective #{row.plan_id}")

        elif command_id == "one_shot_plan":
            self._push_streaming_detail(
                row=row,
                command=[
                    "erk",
                    "objective",
                    "plan",
                    str(row.plan_id),
                    "--one-shot",
                ],
                title=f"Implement (One-Shot) #{row.plan_id}",
                timeout=600.0,
                on_success=None,
            )

        elif command_id == "check_objective":
            self._push_streaming_detail(
                row=row,
                command=["erk", "objective", "check", str(row.plan_id)],
                title=f"Check Objective #{row.plan_id}",
                timeout=30.0,
                on_success=None,
            )

        elif command_id == "close_objective":
            self._push_streaming_detail(
                row=row,
                command=["erk", "objective", "close", str(row.plan_id), "--force"],
                title=f"Close Objective #{row.plan_id}",
                timeout=30.0,
                on_success=None,
            )

        elif command_id == "codespace_run_plan":
            cmd = f"erk codespace run objective plan {row.plan_id}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

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
            if row.plan_url:
                self._provider.browser.launch(row.plan_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened issue #{row.plan_id}")

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

    @on(PlanDataTable.LearnClicked)
    def on_learn_clicked(self, event: PlanDataTable.LearnClicked) -> None:
        """Handle click on learn cell - open learn plan issue, PR, or workflow run in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            # Build URL based on which field is set
            # PR takes priority (plan_completed state)
            if row.learn_plan_pr is not None and row.plan_url:
                pr_url = _build_github_url(row.plan_url, "pull", row.learn_plan_pr)
                self._provider.browser.launch(pr_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened learn PR #{row.learn_plan_pr}")
            elif row.learn_plan_issue is not None and row.plan_url:
                issue_url = _build_github_url(row.plan_url, "issues", row.learn_plan_issue)
                self._provider.browser.launch(issue_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened learn issue #{row.learn_plan_issue}")
            elif row.learn_run_url is not None:
                self._provider.browser.launch(row.learn_run_url)
                if self._status_bar is not None:
                    # Extract run ID from URL for status message
                    run_id = row.learn_run_url.rsplit("/", 1)[-1]
                    self._status_bar.set_message(f"Opened learn workflow run {run_id}")

    @on(PlanDataTable.ObjectiveClicked)
    def on_objective_clicked(self, event: PlanDataTable.ObjectiveClicked) -> None:
        """Handle click on objective cell - open objective issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.objective_issue is not None and row.plan_url:
                self._provider.browser.launch(
                    _build_github_url(row.plan_url, "issues", row.objective_issue)
                )
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened objective #{row.objective_issue}")
