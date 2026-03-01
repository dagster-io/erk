"""Main Textual application for erk dash interactive mode."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Input, Label

from erk.tui.actions.filter_actions import FilterActionsMixin
from erk.tui.actions.navigation import NavigationActionsMixin
from erk.tui.actions.palette import PaletteActionsMixin
from erk.tui.commands.provider import MainListCommandProvider
from erk.tui.data.types import FetchTimings, PlanFilters, PlanRowData
from erk.tui.filtering.logic import filter_plans
from erk.tui.filtering.types import FilterMode, FilterState
from erk.tui.operations.logic import build_github_url
from erk.tui.operations.streaming import StreamingOperationsMixin
from erk.tui.operations.workers import BackgroundWorkersMixin
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
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
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


class ErkDashApp(
    NavigationActionsMixin,
    FilterActionsMixin,
    PaletteActionsMixin,
    StreamingOperationsMixin,
    BackgroundWorkersMixin,
    App,
):
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
        Binding("o", "toggle_objective_filter", "Objective", show=False),
        Binding("p", "open_pr", "Open PR"),
        Binding("n", "open_run", "Run"),
        Binding("c", "view_comments", "Comments", show=False),
        Binding("h", "view_checks", "Checks", show=False),
        Binding("i", "show_implement", "Implement"),
        Binding("v", "view_plan_body", "View", show=False),
        Binding("l", "launch", "Launch"),
        Binding("slash", "start_filter", "Filter", key_display="/"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("1", "switch_view_plans", "Plans", show=False),
        Binding("2", "switch_view_learn", "Learn", show=False),
        Binding("3", "switch_view_objectives", "Objectives", show=False),
        Binding("t", "toggle_stack_filter", "Stack", show=False),
        Binding("x", "one_shot_prompt", "One-Shot"),
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
        cmux_integration: bool = False,
    ) -> None:
        """Initialize the dashboard app.

        Args:
            provider: Data provider for fetching plan data
            filters: Filter options for the plan list
            refresh_interval: Seconds between auto-refresh (0 to disable)
            initial_sort: Initial sort state (defaults to by plan number)
            cmux_integration: Whether cmux workspace integration is enabled
        """
        super().__init__()
        self._provider = provider
        self._plan_filters = filters
        self._refresh_interval = refresh_interval
        self._cmux_integration = cmux_integration
        self._table: PlanDataTable | None = None
        self._status_bar: StatusBar | None = None
        self._filter_input: Input | None = None
        self._all_rows: list[PlanRowData] = []  # Unfiltered data
        self._rows: list[PlanRowData] = []  # Currently displayed (possibly filtered)
        self._refresh_task: asyncio.Task | None = None
        self._loading = True
        self._filter_state = FilterState.initial()
        self._stack_filter_branches: frozenset[str] | None = None
        self._stack_filter_label: str | None = None
        self._objective_filter_issue: int | None = None
        self._objective_filter_label: str | None = None
        self._sort_state = initial_sort if initial_sort is not None else SortState.initial()
        self._activity_by_plan: dict[int, BranchActivity] = {}
        self._activity_loading = False
        self._view_mode: ViewMode = ViewMode.PLANS
        self._view_bar: ViewBar | None = None
        self._data_cache: dict[tuple[str, ...], list[PlanRowData]] = {}

    def _display_name_for_view(self, mode: ViewMode) -> str:
        """Get the display name for a view mode.

        Args:
            mode: The view mode to get a display name for

        Returns:
            Display name string
        """
        if mode == ViewMode.PLANS:
            return "Planned PRs"
        return get_view_config(mode).display_name

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        yield ViewBar(
            active_view=self._view_mode,
            plans_display_name=self._display_name_for_view(ViewMode.PLANS),
        )
        with Container(id="main-container"):
            yield Label(
                f"Loading {self._display_name_for_view(ViewMode.PLANS).lower()}...",
                id="loading-message",
            )
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
            exclude_labels=view_config.exclude_labels,
        )

        fetch_timings: FetchTimings | None = None
        try:
            # Run sync fetch in executor to avoid blocking
            loop = asyncio.get_running_loop()
            rows, fetch_timings = await loop.run_in_executor(
                None, self._provider.fetch_plans, active_filters
            )

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
        self._update_table(
            rows, update_time, duration, fetched_mode=fetched_mode, fetch_timings=fetch_timings
        )

    def _update_table(
        self,
        rows: list[PlanRowData],
        update_time: str | None,
        duration: float | None,
        *,
        fetched_mode: ViewMode,
        fetch_timings: FetchTimings | None = None,
    ) -> None:
        """Update table with new data.

        Args:
            rows: Plan data to display
            update_time: Formatted time of this update
            duration: Duration of the fetch in seconds
            fetched_mode: The view mode that was active when the fetch started.
                Data is cached under that mode's labels and the display is only
                updated if it still matches the current view.
            fetch_timings: Optional timing breakdown for each fetch phase
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
            noun = self._display_name_for_view(self._view_mode).lower()
            self._status_bar.set_plan_count(len(self._rows), noun=noun)
            self._status_bar.set_sort_mode(self._sort_state.display_label)
            if update_time is not None:
                self._status_bar.set_last_update(update_time, duration, fetch_timings=fetch_timings)

    def _apply_filter_and_sort(self, rows: list[PlanRowData]) -> list[PlanRowData]:
        """Apply current filter and sort to rows.

        Filter pipeline: objective filter → stack filter → text filter → sort.

        Args:
            rows: Raw rows to process

        Returns:
            Filtered and sorted rows
        """
        # Apply objective filter first
        if self._objective_filter_issue is not None:
            rows = [r for r in rows if r.objective_issue == self._objective_filter_issue]

        # Apply stack filter
        if self._stack_filter_branches is not None:
            rows = [
                r
                for r in rows
                if r.pr_head_branch is not None and r.pr_head_branch in self._stack_filter_branches
            ]

        # Apply text filter
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
        # Server-side label AND logic now correctly splits Plans/Learn.
        # Keep as pass-through safety net.
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

    def _switch_view(self, mode: ViewMode) -> None:
        """Switch to a different view mode.

        Caches current data, reconfigures the table, and loads new data.

        Args:
            mode: The view mode to switch to
        """
        if mode == self._view_mode:
            return

        # Clear filters when switching views
        self._stack_filter_branches = None
        self._stack_filter_label = None
        self._objective_filter_issue = None
        self._objective_filter_label = None

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
                noun = self._display_name_for_view(mode).lower()
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

    # --- Event handlers (must be on concrete class for Textual @on discovery) ---

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

    @on(ViewBar.ViewTabClicked)
    def on_view_tab_clicked(self, event: ViewBar.ViewTabClicked) -> None:
        """Handle click on a view bar tab - switch to that view."""
        self._switch_view(event.view_mode)

    @on(PlanDataTable.PlanClicked)
    def on_plan_clicked(self, event: PlanDataTable.PlanClicked) -> None:
        """Handle click on plan cell - open issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.plan_url:
                self._provider.browser.launch(row.plan_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened plan #{row.plan_id}")

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
                    run_id = row.run_url.rsplit("/", 1)[-1]
                    self._status_bar.set_message(f"Opened run {run_id}")

    @on(PlanDataTable.DepsClicked)
    def on_deps_clicked(self, event: PlanDataTable.DepsClicked) -> None:
        """Handle click on head cell - open first blocking head plan in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.objective_head_plans:
                display, url = row.objective_head_plans[0]
                self._provider.browser.launch(url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened plan {display}")

    @on(PlanDataTable.ObjectiveClicked)
    def on_objective_clicked(self, event: PlanDataTable.ObjectiveClicked) -> None:
        """Handle click on objective cell - open objective issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.objective_issue is not None and row.plan_url:
                self._provider.browser.launch(
                    build_github_url(row.plan_url, "issues", row.objective_issue)
                )
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened objective #{row.objective_issue}")
