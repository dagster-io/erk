"""Run table widget for TUI dashboard Runs tab."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.events import Click
from textual.message import Message
from textual.widgets import DataTable

from erk.tui.data.types import RunRowData

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class RunDataTable(DataTable):
    """DataTable subclass for displaying workflow runs.

    Manages column configuration and row population from RunRowData.
    Uses row selection mode (not cell selection) for simpler navigation.
    """

    class RunClicked(Message):
        """Posted when user clicks run-id column on a row."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    class PrClicked(Message):
        """Posted when user clicks pr column on a row with a PR URL."""

        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index

    def __init__(self) -> None:
        super().__init__(cursor_type="row")
        self._rows: list[RunRowData] = []
        self._run_id_column_index: int = 0
        self._pr_column_index: int | None = None

    def action_cursor_left(self) -> None:
        """Delegate left arrow to app's previous_view action."""
        cast("ErkDashApp", self.app).action_previous_view()

    def action_cursor_right(self) -> None:
        """Delegate right arrow to app's next_view action."""
        cast("ErkDashApp", self.app).action_next_view()

    def on_mount(self) -> None:
        """Configure columns when widget is mounted."""
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Add columns for the runs table.

        Columns: run-id, status, submitted, workflow, pr, branch, chks
        """
        col_index = 0
        self._run_id_column_index = col_index
        self.add_column("run-id", key="run_id", width=12)
        col_index += 1
        self.add_column("status", key="status", width=14)
        col_index += 1
        self.add_column("submitted", key="submitted", width=12)
        col_index += 1
        self.add_column("workflow", key="workflow", width=16)
        col_index += 1
        self._pr_column_index = col_index
        self.add_column("pr", key="pr", width=8)
        col_index += 1
        self.add_column("branch", key="branch", width=40)
        col_index += 1
        self.add_column("chks", key="chks", width=8)
        col_index += 1

    def populate(self, rows: list[RunRowData]) -> None:
        """Populate table with run data, preserving cursor position.

        Args:
            rows: List of RunRowData to display
        """
        selected_key: str | None = None
        if self._rows and self.cursor_row is not None and 0 <= self.cursor_row < len(self._rows):
            selected_key = self._rows[self.cursor_row].run_id

        saved_cursor_row = self.cursor_row

        self._rows = rows
        self.clear()

        for row in rows:
            values = self._row_to_values(row)
            self.add_row(*values, key=row.run_id)

        if rows:
            if selected_key is not None:
                for idx, row in enumerate(rows):
                    if row.run_id == selected_key:
                        self.move_cursor(row=idx)
                        return

            if saved_cursor_row is not None and saved_cursor_row >= 0:
                target_row = min(saved_cursor_row, len(rows) - 1)
                self.move_cursor(row=target_row)

    def _row_to_values(self, row: RunRowData) -> tuple[str, ...]:
        """Convert RunRowData to table cell values.

        Args:
            row: Run row data

        Returns:
            Tuple of cell values matching column order
        """
        run_id_cell = row.run_id_display
        if row.run_url:
            run_id_cell = f"[link={row.run_url}]{row.run_id_display}[/link]"

        pr_cell = row.pr_display
        if row.pr_url and row.pr_number is not None:
            pr_cell = f"[link={row.pr_url}]{row.pr_display}[/link]"

        return (
            run_id_cell,
            row.status_display,
            row.submitted_display,
            row.workflow_name,
            pr_cell,
            row.branch_display,
            row.checks_display,
        )

    def get_selected_row_data(self) -> RunRowData | None:
        """Get the RunRowData for the currently selected row.

        Returns:
            RunRowData for selected row, or None if no selection
        """
        cursor_row = self.cursor_row
        if cursor_row is None or cursor_row < 0 or cursor_row >= len(self._rows):
            return None
        return self._rows[cursor_row]

    def on_click(self, event: Click) -> None:
        """Detect clicks on specific columns and post appropriate messages.

        Args:
            event: Click event from Textual
        """
        coord = self.hover_coordinate
        if coord is None:
            return

        row_index = coord.row
        col_index = coord.column

        if col_index == self._run_id_column_index:
            if row_index < len(self._rows) and self._rows[row_index].run_url:
                self.post_message(self.RunClicked(row_index))
                event.prevent_default()
                event.stop()
                return

        if self._pr_column_index is not None and col_index == self._pr_column_index:
            if row_index < len(self._rows) and self._rows[row_index].pr_url:
                self.post_message(self.PrClicked(row_index))
                event.prevent_default()
                event.stop()
                return
