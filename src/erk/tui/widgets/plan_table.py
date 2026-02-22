"""Plan table widget for TUI dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.events import Click
from textual.message import Message
from textual.widgets import DataTable

from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.views.types import ViewMode
from erk_shared.context.types import PlanBackendType

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class PlanDataTable(DataTable):
    """DataTable subclass for displaying plans.

    Manages column configuration and row population from PlanRowData.
    Uses row selection mode (not cell selection) for simpler navigation.
    """

    class LocalWtClicked(Message):
        """Posted when user clicks local-wt column on a row with existing worktree."""

        def __init__(self, row_index: int) -> None:
            """Initialize the message.

            Args:
                row_index: Index of the clicked row
            """
            super().__init__()
            self.row_index = row_index

    class RunIdClicked(Message):
        """Posted when user clicks run-id column on a row with a run URL."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class PrClicked(Message):
        """Posted when user clicks pr column on a row with a PR URL."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class PlanClicked(Message):
        """Posted when user clicks plan column on a row with an issue URL."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class BranchClicked(Message):
        """Posted when user clicks branch column on a row."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class LearnClicked(Message):
        """Posted when user clicks learn column on a row with a learn plan issue or PR."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class ObjectiveClicked(Message):
        """Posted when user clicks objective column on a row with an objective issue."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    def __init__(self, plan_filters: PlanFilters, *, plan_backend: PlanBackendType) -> None:
        """Initialize table with column configuration based on filters.

        Args:
            plan_filters: Filter options that determine which columns to show
            plan_backend: Plan backend type ("github" or "draft_pr")
        """
        super().__init__(cursor_type="row")
        self._plan_filters = plan_filters
        self._plan_backend = plan_backend
        self._view_mode: ViewMode = ViewMode.PLANS
        self._rows: list[PlanRowData] = []
        self._plan_column_index: int = 0  # Always first column
        self._objective_column_index: int | None = None
        self._pr_column_index: int | None = None
        self._branch_column_index: int | None = None
        self._learn_column_index: int | None = None
        self._local_wt_column_index: int | None = None
        self._run_id_column_index: int | None = None
        self._stage_column_index: int | None = None

    @property
    def local_wt_column_index(self) -> int | None:
        """Get the column index for the local-wt column.

        Returns:
            Column index (0-based), or None if columns not yet set up.
        """
        return self._local_wt_column_index

    def action_cursor_left(self) -> None:
        """Delegate left arrow to app's previous_view action."""
        cast("ErkDashApp", self.app).action_previous_view()

    def action_cursor_right(self) -> None:
        """Delegate right arrow to app's next_view action."""
        cast("ErkDashApp", self.app).action_next_view()

    def reconfigure(
        self, *, plan_filters: PlanFilters, view_mode: ViewMode, plan_backend: PlanBackendType
    ) -> None:
        """Reconfigure the table for a new view mode.

        Clears existing columns and rows, then sets up new columns
        appropriate for the view mode.

        Args:
            plan_filters: New filter options for column configuration
            view_mode: The new view mode
            plan_backend: Plan backend type ("github" or "draft_pr")
        """
        self._plan_filters = plan_filters
        self._view_mode = view_mode
        self._plan_backend = plan_backend
        # Reset column indices before _setup_columns rebuilds them
        self._plan_column_index = 0
        self._objective_column_index = None
        self._pr_column_index = None
        self._branch_column_index = None
        self._learn_column_index = None
        self._local_wt_column_index = None
        self._run_id_column_index = None
        self._stage_column_index = None
        self.clear(columns=True)
        self._setup_columns()

    def on_mount(self) -> None:
        """Configure columns when widget is mounted."""
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Add columns based on current filter settings and view mode.

        Tracks column indices for click detection on plan, branch, local-wt, etc.
        Objectives view uses enriched columns (plan, progress, next, updated, author).
        """
        col_index = 0
        # In draft_pr mode, first column shows PR number not issue number
        if self._view_mode == ViewMode.OBJECTIVES:
            plan_col_header = "issue"
        elif self._plan_backend == "draft_pr":
            plan_col_header = "pr"
        else:
            plan_col_header = "plan"
        self.add_column(plan_col_header, key="plan", width=6)
        col_index += 1

        # Objectives view: fully independent column set, return early
        if self._view_mode == ViewMode.OBJECTIVES:
            self.add_column("title", key="title", width=50)
            col_index += 1
            self.add_column("prog", key="progress", width=5)
            col_index += 1
            self.add_column("fly", key="in_flight", width=3)
            col_index += 1
            self.add_column("next node", key="next_node", width=50)
            col_index += 1
            self.add_column("deps", key="deps", width=12)
            col_index += 1
            self.add_column("updated", key="updated", width=7)
            col_index += 1
            self.add_column("created by", key="author", width=12)
            col_index += 1
            return

        if self._plan_backend == "draft_pr":
            self._stage_column_index = col_index
            self.add_column("stage", key="stage", width=11)
            col_index += 1
            self.add_column("created", key="created", width=7)
            col_index += 1
        self.add_column("obj", key="objective", width=5)
        self._objective_column_index = col_index
        col_index += 1

        # Plans view: plan, [stage, created,] obj, loc, branch,
        # run-id, run, [created,] author, ...
        self.add_column("loc", key="location", width=3)
        col_index += 1
        self._branch_column_index = col_index
        self.add_column("branch", key="branch", width=42)
        col_index += 1
        self._run_id_column_index = col_index
        self.add_column("run-id", key="run_id", width=10)
        col_index += 1
        self.add_column("run", key="run_state", width=3)
        col_index += 1
        if self._plan_backend != "draft_pr":
            self.add_column("created", key="created", width=7)
            col_index += 1
        self.add_column("author", key="author", width=9)
        col_index += 1

        if self._plan_filters.show_pr_column:
            self._pr_column_index = col_index
            self.add_column("pr", key="pr", width=8)
            col_index += 1
        self.add_column("chks", key="chks", width=8)
        col_index += 1
        self.add_column("cmts", key="comments", width=5)
        col_index += 1
        self.add_column("lrn", key="learn")
        self._learn_column_index = col_index
        col_index += 1
        self._local_wt_column_index = col_index
        self.add_column("local-wt", key="local_wt", width=14)
        col_index += 1
        self.add_column("local-impl", key="local_impl", width=10)
        col_index += 1
        self.add_column("remote-impl", key="remote_impl", width=10)
        col_index += 1

    def populate(self, rows: list[PlanRowData]) -> None:
        """Populate table with plan data, preserving cursor position.

        If the selected plan still exists, cursor stays on it.
        If the selected plan disappeared, cursor stays at the same row index.

        Args:
            rows: List of PlanRowData to display
        """
        # Save current selection by issue number (row key)
        selected_key: str | None = None
        if self._rows and self.cursor_row is not None and 0 <= self.cursor_row < len(self._rows):
            selected_key = str(self._rows[self.cursor_row].plan_id)

        # Save cursor row index for fallback (move up if plan disappears)
        saved_cursor_row = self.cursor_row

        self._rows = rows
        self.clear()

        for row in rows:
            values = self._row_to_values(row)
            self.add_row(*values, key=str(row.plan_id))

        # Restore cursor position
        if rows:
            # Try to restore by key (issue number) first
            if selected_key is not None:
                for idx, row in enumerate(rows):
                    if str(row.plan_id) == selected_key:
                        self.move_cursor(row=idx)
                        return

            # Plan disappeared - stay at same row index, clamped to valid range
            if saved_cursor_row is not None and saved_cursor_row >= 0:
                target_row = min(saved_cursor_row, len(rows) - 1)
                self.move_cursor(row=target_row)

    def _row_to_values(self, row: PlanRowData) -> tuple[str | Text, ...]:
        """Convert PlanRowData to table cell values.

        Args:
            row: Plan row data

        Returns:
            Tuple of cell values matching column order
        """
        # Format issue number - colorize if clickable
        plan_cell: str | Text = f"#{row.plan_id}"
        if row.plan_url:
            plan_cell = Text(plan_cell, style="cyan underline")

        # Objectives view: plan, progress, fly, next, updated, author
        if self._view_mode == ViewMode.OBJECTIVES:
            return (
                plan_cell,
                row.full_title,
                row.objective_progress_display,
                row.objective_in_flight_display,
                Text(row.objective_next_node_display),
                row.objective_deps_display,
                row.updated_display,
                row.author,
            )

        # Format worktree
        if row.exists_locally:
            wt_cell = row.worktree_name
        else:
            wt_cell = "-"

        # Format learn cell - use icon-only for table, colorize if clickable
        learn_cell: str | Text = row.learn_display_icon
        if (
            row.learn_plan_issue is not None
            or row.learn_plan_pr is not None
            or row.learn_run_url is not None
        ):
            learn_cell = Text(row.learn_display_icon, style="cyan underline")

        # Format objective cell - colorize if clickable
        objective_cell: str | Text = row.objective_display
        if row.objective_issue is not None:
            objective_cell = Text(row.objective_display, style="cyan underline")

        # Compact location emoji: 💻 = local checkout, 🌐 = remote run
        location_parts: list[str] = []
        if row.exists_locally:
            location_parts.append("\U0001f4bb")
        if row.run_url is not None:
            location_parts.append("\U0001f310")
        location_cell = "".join(location_parts) if location_parts else "-"

        # run-id and run-state (always shown)
        run_id: str | Text = _strip_rich_markup(row.run_id_display)
        if row.run_url:
            run_id = Text(run_id, style="cyan underline")
        run_state_text = _strip_rich_markup(row.run_state_display)
        run_state_emoji = run_state_text.split(" ", 1)[0] if run_state_text.strip() else "-"

        # Build values list based on columns
        values: list[str | Text] = [
            plan_cell,
        ]
        if self._plan_backend == "draft_pr":
            stage_display = _strip_rich_markup(row.lifecycle_display)
            values.append(stage_display)
            values.append(row.created_display)
        values.extend(
            [
                objective_cell,
                location_cell,
                row.pr_head_branch or row.worktree_branch or "-",
                run_id,
                run_state_emoji,
            ]
        )
        if self._plan_backend != "draft_pr":
            values.append(row.created_display)
        values.append(row.author)

        checks_display = _strip_rich_markup(row.checks_display)
        comments_display = _strip_rich_markup(row.comments_display)
        if self._plan_filters.show_pr_column:
            # Strip Rich markup and colorize if clickable
            pr_display = _strip_rich_markup(row.pr_display)
            if row.pr_url:
                pr_display = Text(pr_display, style="cyan underline")
            values.extend([pr_display, checks_display, comments_display, learn_cell])
        else:
            values.extend([checks_display, comments_display, learn_cell])
        values.extend([wt_cell, row.local_impl_display])
        remote_impl = _strip_rich_markup(row.remote_impl_display)
        values.append(remote_impl)

        return tuple(values)

    def get_selected_row_data(self) -> PlanRowData | None:
        """Get the PlanRowData for the currently selected row.

        Returns:
            PlanRowData for selected row, or None if no selection
        """
        cursor_row = self.cursor_row
        if cursor_row is None or cursor_row < 0 or cursor_row >= len(self._rows):
            return None
        return self._rows[cursor_row]

    def on_click(self, event: Click) -> None:
        """Detect clicks on specific columns and post appropriate messages.

        Posts LocalWtClicked event if:
        - Click is on the local-wt column
        - The row has an existing local worktree (not '-')

        Posts RunIdClicked event if:
        - Click is on the run-id column
        - The row has a run URL

        Stops event propagation to prevent default row selection behavior when
        a column-specific click is detected.

        Args:
            event: Click event from Textual
        """
        coord = self.hover_coordinate
        if coord is None:
            return

        row_index = coord.row
        col_index = coord.column

        # Check plan column (issue number)
        if col_index == self._plan_column_index:
            if row_index < len(self._rows) and self._rows[row_index].plan_url:
                self.post_message(self.PlanClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check objective column - post event if objective issue exists
        if self._objective_column_index is not None and col_index == self._objective_column_index:
            if row_index < len(self._rows) and self._rows[row_index].objective_issue is not None:
                self.post_message(self.ObjectiveClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check branch column - post event for clipboard copy
        if self._branch_column_index is not None and col_index == self._branch_column_index:
            if row_index < len(self._rows):
                self.post_message(self.BranchClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check learn column - post event if learn plan issue, PR, or run URL exists
        if self._learn_column_index is not None and col_index == self._learn_column_index:
            row = self._rows[row_index] if row_index < len(self._rows) else None
            if row is not None and (
                row.learn_plan_issue is not None
                or row.learn_plan_pr is not None
                or row.learn_run_url is not None
            ):
                self.post_message(self.LearnClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check PR column
        if self._pr_column_index is not None and col_index == self._pr_column_index:
            if row_index < len(self._rows) and self._rows[row_index].pr_url:
                self.post_message(self.PrClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check local-wt column - post event if worktree exists
        if self._local_wt_column_index is not None and col_index == self._local_wt_column_index:
            if row_index < len(self._rows) and self._rows[row_index].exists_locally:
                self.post_message(self.LocalWtClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        # Check run-id column - post event if run URL exists
        if self._run_id_column_index is not None and col_index == self._run_id_column_index:
            if row_index < len(self._rows) and self._rows[row_index].run_url:
                self.post_message(self.RunIdClicked(row_index))
                event.prevent_default()
                event.stop()
                return


def _strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text.

    Args:
        text: Text potentially containing Rich markup like [link=...]...[/link]

    Returns:
        Plain text with markup removed
    """
    import re

    # Remove [tag=value] and [/tag] patterns
    return re.sub(r"\[/?[^\]]+\]", "", text)
