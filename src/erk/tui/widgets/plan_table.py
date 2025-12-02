"""Plan table widget for TUI dashboard."""

from textual.widgets import DataTable

from erk.tui.data.types import PlanFilters, PlanRowData


class PlanDataTable(DataTable):
    """DataTable subclass for displaying plans.

    Manages column configuration and row population from PlanRowData.
    Uses row selection mode (not cell selection) for simpler navigation.
    """

    def __init__(self, plan_filters: PlanFilters) -> None:
        """Initialize table with column configuration based on filters.

        Args:
            plan_filters: Filter options that determine which columns to show
        """
        super().__init__(cursor_type="row")
        self._plan_filters = plan_filters
        self._rows: list[PlanRowData] = []

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
        """Add columns based on current filter settings."""
        self.add_column("plan", key="plan")
        self.add_column("title", key="title")
        if self._plan_filters.show_prs:
            self.add_column("pr", key="pr")
            self.add_column("chks", key="chks")
        self.add_column("local-wt", key="local_wt")
        self.add_column("local-impl", key="local_impl")
        if self._plan_filters.show_runs:
            self.add_column("remote-impl", key="remote_impl")
            self.add_column("run-id", key="run_id")
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

    def _row_to_values(self, row: PlanRowData) -> tuple[str, ...]:
        """Convert PlanRowData to table cell values.

        Args:
            row: Plan row data

        Returns:
            Tuple of cell values matching column order
        """
        # Format issue number
        plan_cell = f"#{row.issue_number}"

        # Format worktree
        if row.exists_locally:
            wt_cell = row.worktree_name
        else:
            wt_cell = "-"

        # Build values list based on columns
        values: list[str] = [plan_cell, row.title]
        if self._plan_filters.show_prs:
            # Strip Rich markup for plain text display in Textual
            pr_display = _strip_rich_markup(row.pr_display)
            checks_display = _strip_rich_markup(row.checks_display)
            values.extend([pr_display, checks_display])
        values.extend([wt_cell, row.local_impl_display])
        if self._plan_filters.show_runs:
            remote_impl = _strip_rich_markup(row.remote_impl_display)
            run_id = _strip_rich_markup(row.run_id_display)
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
