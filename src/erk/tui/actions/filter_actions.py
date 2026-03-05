"""Filter action handlers for TUI application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erk.tui.filtering.types import FilterState
from erk.tui.sorting.types import BranchActivity, SortKey

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class FilterActionsMixin:
    """Mixin providing filter and sort action handlers.

    Includes action_start_filter, action_toggle_stack_filter,
    action_toggle_objective_filter, action_toggle_sort,
    and related helpers.
    """

    def action_start_filter(self: ErkDashApp) -> None:
        """Activate filter mode and focus the input."""
        if self._filter_input is None:
            return
        self._filter_state = self._filter_state.activate()
        self._filter_input.disabled = False
        self._filter_input.add_class("visible")
        self._filter_input.focus()

    def action_toggle_stack_filter(self: ErkDashApp) -> None:
        """Toggle stack filter for the focused row's Graphite stack.

        If stack filter is active, clears it (toggle off).
        If no row selected or row has no branch, shows status message.
        If branch is not in a Graphite stack, shows status message.
        Otherwise, filters table to only show rows in the same stack.
        """
        # Toggle off if already active
        if self._stack_filter_branches is not None:
            self._clear_stack_filter()
            return

        row = self._get_selected_row()
        if row is None or row.pr_head_branch is None:
            if self._status_bar is not None:
                self._status_bar.set_message("No branch for stack filter")
            return

        stack = self._provider.get_branch_stack(row.pr_head_branch)
        if stack is None:
            if self._status_bar is not None:
                self._status_bar.set_message("Not in a Graphite stack")
            return

        self._stack_filter_branches = frozenset(stack)
        self._stack_filter_label = row.pr_head_branch
        self._apply_filter()

        if self._status_bar is not None:
            self._status_bar.set_message(f"Stack: {row.pr_head_branch} ({len(stack)})")

    def _clear_stack_filter(self: ErkDashApp) -> None:
        """Clear the stack filter and restore all rows."""
        self._stack_filter_branches = None
        self._stack_filter_label = None
        self._apply_filter()
        if self._status_bar is not None:
            self._status_bar.set_message(None)

    def action_toggle_objective_filter(self: ErkDashApp) -> None:
        """Toggle objective filter for the focused row's objective.

        If objective filter is active, clears it (toggle off).
        If no row selected or row has no objective_issue, shows status message.
        Otherwise, filters table to only show rows sharing the same objective.
        """
        # Toggle off if already active
        if self._objective_filter_issue is not None:
            self._clear_objective_filter()
            return

        row = self._get_selected_row()
        if row is None:
            return

        if row.objective_issue is None:
            if self._status_bar is not None:
                self._status_bar.set_message("Plan not linked to an objective")
            return

        self._objective_filter_issue = row.objective_issue
        self._objective_filter_label = str(row.objective_issue)
        self._apply_filter()

        count = len(self._rows)
        if self._status_bar is not None:
            self._status_bar.set_message(f"Objective: #{row.objective_issue} ({count})")

    def _clear_objective_filter(self: ErkDashApp) -> None:
        """Clear the objective filter and restore all rows."""
        self._objective_filter_issue = None
        self._objective_filter_label = None
        self._apply_filter()
        if self._status_bar is not None:
            self._status_bar.set_message(None)

    def action_toggle_all_users(self: ErkDashApp) -> None:
        """Toggle between showing only my plans and all users' plans.

        Since the creator filter is server-side (GitHub API), toggling
        requires clearing the data cache and re-fetching.
        """
        self._show_all_users = not self._show_all_users
        self._data_cache.clear()

        if self._show_all_users:
            label = "all"
        else:
            label = self._original_creator or "me"

        if self._status_bar is not None:
            self._status_bar.set_author_filter(label)

        self.action_refresh()

        if self._show_all_users:
            self.notify("Showing all users", timeout=2)
        else:
            self.notify("Showing my plans", timeout=2)

    def action_toggle_sort(self: ErkDashApp) -> None:
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

    def _on_activity_loaded(self: ErkDashApp, activity: dict[int, BranchActivity]) -> None:
        """Handle activity data loaded - resort the table."""
        self._activity_by_plan = activity
        self._activity_loading = False

        # Re-sort with new activity data
        self._rows = self._apply_filter_and_sort(self._all_rows)
        if self._table is not None:
            self._table.populate(self._rows)

    def _apply_filter(self: ErkDashApp) -> None:
        """Apply current filter query to the table."""
        self._rows = self._apply_filter_and_sort(self._all_rows)

        if self._table is not None:
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(
                len(self._rows), noun=self._display_name_for_view(self._view_mode).lower()
            )

    def _exit_filter_mode(self: ErkDashApp) -> None:
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
            self._status_bar.set_plan_count(
                len(self._rows), noun=self._display_name_for_view(self._view_mode).lower()
            )
