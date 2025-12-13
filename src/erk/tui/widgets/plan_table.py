"""Plan table widget for TUI dashboard."""

from rich.text import Text
from textual.events import Click
from textual.message import Message
from textual.widgets import DataTable

from erk.tui.data.types import PlanFilters, PlanRowData


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

    def __init__(self, plan_filters: PlanFilters) -> None:
        """Initialize table with column configuration based on filters.

        Args:
            plan_filters: Filter options that determine which columns to show
        """
        super().__init__(cursor_type="row")
        self._plan_filters = plan_filters
        self._rows: list[PlanRowData] = []
        self._plan_column_index: int = 0  # Always first column
        self._pr_column_index: int | None = None
        self._local_wt_column_index: int | None = None
        self._run_id_column_index: int | None = None

    @property
    def local_wt_column_index(self) -> int | None:
        """Get the column index for the local-wt column.

        Returns:
            Column index (0-based), or None if columns not yet set up.
            The index varies based on show_prs flag:
            - Without PRs: index 2 (plan, title, local-wt)
            - With PRs: index 4 (plan, title, pr, chks, local-wt)
        """
        return self._local_wt_column_index

    def action_cursor_left(self) -> None:
        """Disable left arrow navigation (row mode only)."""
        pass

    def action_cursor_right(self) -> None:
        """Disable right arrow navigation (row mode only)."""
        pass

    def on_mount(self) -> None:
        """Configure columns when widget is mounted."""
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Add columns based on current filter settings.

        Tracks the column index for local-wt to enable click detection.
        """
        col_index = 0
        self.add_column("plan", key="plan")
        col_index += 1
        self.add_column("title", key="title")
        col_index += 1
        if self._plan_filters.show_prs:
            self.add_column("pr", key="pr")
            self._pr_column_index = col_index
            col_index += 1
            self.add_column("chks", key="chks")
            col_index += 1
        self._local_wt_column_index = col_index
        self.add_column("local-wt", key="local_wt")
        col_index += 1
        self.add_column("local-impl", key="local_impl")
        col_index += 1
        if self._plan_filters.show_runs:
            self.add_column("remote-impl", key="remote_impl")
            col_index += 1
            self.add_column("run-id", key="run_id")
            self._run_id_column_index = col_index
            col_index += 1
            self.add_column("run-state", key="run_state")

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
            selected_key = str(self._rows[self.cursor_row].issue_number)

        # Save cursor row index for fallback (move up if plan disappears)
        saved_cursor_row = self.cursor_row

        self._rows = rows
        self.clear()

        for row in rows:
            values = self._row_to_values(row)
            self.add_row(*values, key=str(row.issue_number))

        # Restore cursor position
        if rows:
            # Try to restore by key (issue number) first
            if selected_key is not None:
                for idx, row in enumerate(rows):
                    if str(row.issue_number) == selected_key:
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
        plan_cell: str | Text = f"#{row.issue_number}"
        if row.issue_url:
            plan_cell = Text(plan_cell, style="cyan underline")

        # Format worktree
        if row.exists_locally:
            wt_cell = row.worktree_name
        else:
            wt_cell = "-"

        # Build values list based on columns
        values: list[str | Text] = [plan_cell, row.title]
        if self._plan_filters.show_prs:
            # Strip Rich markup and colorize if clickable
            pr_display = _strip_rich_markup(row.pr_display)
            if row.pr_url:
                pr_display = Text(pr_display, style="cyan underline")
            checks_display = _strip_rich_markup(row.checks_display)
            values.extend([pr_display, checks_display])
        values.extend([wt_cell, row.local_impl_display])
        if self._plan_filters.show_runs:
            remote_impl = _strip_rich_markup(row.remote_impl_display)
            run_id = _strip_rich_markup(row.run_id_display)
            if row.run_url:
                run_id = Text(run_id, style="cyan underline")
            run_state = _strip_rich_markup(row.run_state_display)
            values.extend([remote_impl, run_id, run_state])

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
            if row_index < len(self._rows) and self._rows[row_index].issue_url:
                self.post_message(self.PlanClicked(row_index))
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
