"""Navigation action handlers for TUI application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erk.tui.commands.types import CommandContext
from erk.tui.data.types import PrRowData, RunRowData
from erk.tui.screens.check_runs_screen import CheckRunsScreen
from erk.tui.screens.help_screen import HelpScreen
from erk.tui.screens.launch_screen import LaunchScreen
from erk.tui.screens.objective_nodes_screen import ObjectiveNodesScreen
from erk.tui.screens.plan_body_screen import PlanBodyScreen
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.views.types import ViewMode
from erk_shared.gateway.command_executor.real import RealCommandExecutor

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class NavigationActionsMixin:
    """Mixin providing navigation and detail-view action handlers.

    Includes action_exit_app, action_refresh, action_help, action_launch,
    action_show_detail, action_view_pr_body, action_view_comments,
    action_view_checks, action_cursor_down, action_cursor_up,
    action_open_pr, action_open_run, action_show_implement,
    action_copy_checkout, action_close_pr, and helpers.
    """

    def action_exit_app(self: ErkDashApp) -> None:
        """Quit the application or handle progressive escape from filter mode.

        Progressive escape: all-users -> objective -> stack -> text content -> text mode -> quit.
        """
        from erk.tui.filtering.types import FilterMode

        if self._run_pr_filter_active:
            self._run_pr_filter_active = False
            cached_runs = self._run_data_cache
            if cached_runs is not None:
                self._run_rows = self._get_filtered_run_rows(cached_runs)
                if self._run_table is not None:
                    self._run_table.populate(self._run_rows)
                if self._status_bar is not None:
                    self._status_bar.set_plan_count(len(self._run_rows), noun="runs")
            self.notify("Showing all runs", timeout=2)
            return
        if self._show_all_users:
            self._show_all_users = False
            self._data_cache.clear()
            if self._status_bar is not None:
                self._status_bar.set_author_filter(None)
            self.action_refresh()
            self.notify("Showing my plans", timeout=2)
            return
        if self._objective_filter_issue is not None:
            self._clear_objective_filter()
            return
        if self._stack_filter_branches is not None:
            self._clear_stack_filter()
            return
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

    def action_refresh(self: ErkDashApp) -> None:
        """Refresh plan data and reset countdown timer."""
        # Reset countdown timer
        if self._refresh_interval > 0:
            self._seconds_remaining = int(self._refresh_interval)
        self.run_worker(self._load_data(), exclusive=True)

    def action_help(self: ErkDashApp) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen(view_mode=self._view_mode))

    def action_launch(self: ErkDashApp) -> None:
        """Open the launch screen for quick ACTION command execution."""
        row = self._get_selected_row()
        if row is None:
            return
        ctx = CommandContext(
            row=row,
            view_mode=self._view_mode,
            cmux_integration=self._cmux_integration,
        )
        self.push_screen(LaunchScreen(ctx=ctx), self._on_launch_result)

    def _on_launch_result(self: ErkDashApp, command_id: str | None) -> None:
        """Handle result from the launch screen.

        Args:
            command_id: The selected command ID, or None if cancelled
        """
        if command_id is not None:
            self.execute_palette_command(command_id)

    def action_show_detail(self: ErkDashApp) -> None:
        """Show plan detail modal for selected row."""
        row = self._get_selected_row()
        if row is None:
            return

        # Create executor with injected dependencies
        executor = RealCommandExecutor(
            browser_launch=self._service.browser.launch,
            clipboard_copy=self._service.clipboard.copy,
            close_pr_fn=self._service.close_pr,
            notify_fn=self._notify_with_severity,
            refresh_fn=self.action_refresh,
            dispatch_to_queue_fn=self._service.dispatch_to_queue,
        )

        self.push_screen(
            PlanDetailScreen(
                row=row,
                clipboard=self._service.clipboard,
                browser=self._service.browser,
                executor=executor,
                repo_root=self._service.repo_root,
                view_mode=self._view_mode,
                cmux_integration=self._cmux_integration,
            )
        )

    def action_view_pr_body(self: ErkDashApp) -> None:
        """Display the plan/objective content in a modal (fetched on-demand)."""
        row = self._get_selected_row()
        if row is None:
            return
        content_type = "Objective" if self._view_mode == ViewMode.OBJECTIVES else "Plan"
        # Push screen that will fetch content on-demand
        self.push_screen(
            PlanBodyScreen(
                service=self._service,
                pr_number=row.pr_number,
                pr_body=row.pr_body,
                full_title=row.full_title,
                content_type=content_type,
            )
        )

    def action_view_comments(self: ErkDashApp) -> None:
        """Display unresolved PR review comments in a modal."""
        row = self._get_selected_row()
        if row is None:
            return
        unresolved = row.total_comment_count - row.resolved_comment_count
        if unresolved == 0:
            if self._status_bar is not None:
                self._status_bar.set_message("No unresolved comments")
            return
        self.push_screen(
            UnresolvedCommentsScreen(
                service=self._service,
                pr_number=row.pr_number,
                full_title=row.full_title,
                resolved_count=row.resolved_comment_count,
                total_count=row.total_comment_count,
            )
        )

    def action_view_checks(self: ErkDashApp) -> None:
        """Display failing CI checks in a modal."""
        row = self._get_selected_row()
        if row is None:
            return
        if row.checks_passing is None:
            if self._status_bar is not None:
                self._status_bar.set_message("No checks available")
            return
        if row.checks_passing is True:
            if self._status_bar is not None:
                self._status_bar.set_message("All checks passing")
            return
        passing_count, total_count = row.checks_counts if row.checks_counts is not None else (0, 0)
        self.push_screen(
            CheckRunsScreen(
                service=self._service,
                pr_number=row.pr_number,
                full_title=row.full_title,
                passing_count=passing_count,
                total_count=total_count,
                ci_summary_comment_id=row.ci_summary_comment_id,
            )
        )

    def action_view_nodes(self: ErkDashApp) -> None:
        """Display objective node breakdown in a modal."""
        if self._view_mode != ViewMode.OBJECTIVES:
            return
        row = self._get_selected_row()
        if row is None:
            return
        if not row.pr_body:
            if self._status_bar is not None:
                self._status_bar.set_message("No objective body available")
            return
        self.push_screen(
            ObjectiveNodesScreen(
                provider=self._provider,
                service=self._service,
                pr_number=row.pr_number,
                pr_body=row.pr_body,
                full_title=row.full_title,
            )
        )

    def action_cursor_down(self: ErkDashApp) -> None:
        """Move cursor down (vim j key)."""
        if self._view_mode == ViewMode.RUNS:
            if self._run_table is not None:
                self._run_table.action_cursor_down()
        elif self._table is not None:
            self._table.action_cursor_down()

    def action_cursor_up(self: ErkDashApp) -> None:
        """Move cursor up (vim k key)."""
        if self._view_mode == ViewMode.RUNS:
            if self._run_table is not None:
                self._run_table.action_cursor_up()
        elif self._table is not None:
            self._table.action_cursor_up()

    def action_open_pr(self: ErkDashApp) -> None:
        """Open selected PR in browser, or objective issue in Objectives view."""
        # Runs tab: open the linked PR
        run_row = self._get_selected_run_row()
        if run_row is not None:
            if run_row.pr_url:
                self._service.browser.launch(run_row.pr_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened PR #{run_row.pr_number}")
            else:
                if self._status_bar is not None:
                    self._status_bar.set_message("No PR linked to this run")
            return

        row = self._get_selected_row()
        if row is None:
            return

        if self._view_mode == ViewMode.OBJECTIVES:
            if row.objective_url is not None:
                self._service.browser.launch(row.objective_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened objective #{row.pr_number}")
            else:
                if self._status_bar is not None:
                    self._status_bar.set_message("No URL for this objective")
        else:
            if row.pr_url:
                self._service.browser.launch(row.pr_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened PR #{row.pr_number}")
            else:
                if self._status_bar is not None:
                    self._status_bar.set_message("No PR linked to this plan")

    def action_open_run(self: ErkDashApp) -> None:
        """Open selected workflow run in browser."""
        # Runs tab: open the run URL directly
        run_row = self._get_selected_run_row()
        if run_row is not None:
            if run_row.run_url is not None:
                self._service.browser.launch(run_row.run_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened run {run_row.run_id}")
            return

        row = self._get_selected_row()
        if row is None:
            return

        if row.run_url is not None:
            self._service.browser.launch(row.run_url)
            if self._status_bar is not None:
                run_id = row.run_url.rsplit("/", 1)[-1]
                self._status_bar.set_message(f"Opened run {run_id}")
        else:
            if self._status_bar is not None:
                self._status_bar.set_message("No workflow run linked to this plan")

    def action_show_implement(self: ErkDashApp) -> None:
        """Show implement command in status bar."""
        row = self._get_selected_row()
        if row is None:
            return

        cmd = f"erk implement {row.pr_number}"
        if self._status_bar is not None:
            self._status_bar.set_message(f"Copy: {cmd}")

    def action_copy_checkout(self: ErkDashApp) -> None:
        """Copy checkout command for selected row."""
        row = self._get_selected_row()
        if row is None:
            return
        self._copy_checkout_command(row)

    def action_close_pr(self: ErkDashApp) -> None:
        """Close the selected plan and its linked PRs (async with toast)."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url is None:
            self.notify("Cannot close plan: no issue URL", severity="warning")
            return

        # Show persistent status bar message and run async - no blocking
        op_id = f"close-plan-{row.pr_number}"
        self._start_operation(op_id=op_id, label=f"Closing plan #{row.pr_number}...")
        self._close_pr_async(op_id, row.pr_number, row.pr_url)

    def _copy_checkout_command(self: ErkDashApp, row: PrRowData) -> None:
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
        success = self._service.clipboard.copy(cmd)

        # Show status message
        if self._status_bar is not None:
            if success:
                self._status_bar.set_message(f"Copied: {cmd}")
            else:
                self._status_bar.set_message(f"Clipboard unavailable. Copy manually: {cmd}")

    def _get_selected_row(self: ErkDashApp) -> PrRowData | None:
        """Get currently selected row data.

        Returns None on the Runs tab since Runs uses RunRowData, not PrRowData.
        """
        if self._view_mode == ViewMode.RUNS:
            return None
        if self._table is None:
            return None
        return self._table.get_selected_row_data()

    def _get_selected_run_row(self: ErkDashApp) -> RunRowData | None:
        """Get currently selected run row data.

        Only returns data when on the Runs tab.
        """
        if self._view_mode != ViewMode.RUNS:
            return None
        if self._run_table is None:
            return None
        return self._run_table.get_selected_row_data()
