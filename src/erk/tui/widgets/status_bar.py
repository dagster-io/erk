"""Status bar widget for TUI dashboard."""

from dataclasses import dataclass

from textual.widgets import Static

from erk.tui.data.types import FetchTimings


@dataclass(frozen=True)
class _OperationState:
    """State for a single tracked background operation."""

    label: str
    progress: str


class StatusBar(Static):
    """Footer status bar showing plan count, refresh status, and messages.

    Displays:
    - Plan count
    - Last update time
    - Time until next refresh
    - Action messages (e.g., command to copy)
    - Key bindings hint
    - Active operation progress
    """

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        """Initialize status bar."""
        super().__init__(markup=False)
        self._plan_count = 0
        self._noun = "plans"
        self._seconds_remaining = 0
        self._last_update: str | None = None
        self._fetch_duration: float | None = None
        self._fetch_timings: FetchTimings | None = None
        self._message: str | None = None
        self._sort_mode: str | None = None
        self._author_filter: str | None = None
        self._operations: dict[str, _OperationState] = {}
        self._last_updated_op_id: str | None = None

    def set_plan_count(self, count: int, *, noun: str) -> None:
        """Update the plan count display.

        Args:
            count: Number of items currently displayed
            noun: The noun to display (e.g., "plans", "learn", "objectives")
        """
        self._plan_count = count
        self._noun = noun
        self._update_display()

    def set_refresh_countdown(self, seconds: int) -> None:
        """Update the refresh countdown.

        Args:
            seconds: Seconds until next refresh
        """
        self._seconds_remaining = seconds
        self._update_display()

    def set_message(self, message: str | None) -> None:
        """Set or clear a transient status message.

        Args:
            message: Message to display, or None to clear
        """
        self._message = message
        self._update_display()

    def start_operation(self, *, op_id: str, label: str) -> None:
        """Register a new background operation.

        Args:
            op_id: Unique identifier for the operation (e.g., "land-pr-456")
            label: Human-readable label (e.g., "Landing PR #456...")
        """
        self._operations[op_id] = _OperationState(label=label, progress="")
        self._last_updated_op_id = op_id
        self.add_class("running")
        self._update_display()

    def update_operation(self, *, op_id: str, progress: str) -> None:
        """Update the latest progress line for an operation.

        Args:
            op_id: Operation identifier
            progress: Latest progress text (e.g., stdout line from subprocess)
        """
        if op_id not in self._operations:
            return
        self._operations[op_id] = _OperationState(
            label=self._operations[op_id].label,
            progress=progress,
        )
        self._last_updated_op_id = op_id
        self._update_display()

    def finish_operation(self, *, op_id: str) -> None:
        """Remove a completed operation.

        Args:
            op_id: Operation identifier to remove
        """
        self._operations.pop(op_id, None)
        if not self._operations:
            self.remove_class("running")
        self._update_display()

    def set_last_update(
        self,
        time_str: str,
        duration_secs: float | None = None,
        *,
        fetch_timings: FetchTimings | None = None,
    ) -> None:
        """Set the last update time.

        Args:
            time_str: Formatted time string (e.g., "14:30:45")
            duration_secs: Duration of the fetch in seconds, or None
            fetch_timings: Optional timing breakdown for each fetch phase
        """
        self._last_update = time_str
        self._fetch_duration = duration_secs
        self._fetch_timings = fetch_timings
        self._update_display()

    def set_sort_mode(self, mode: str) -> None:
        """Set the current sort mode display.

        Args:
            mode: Sort mode label (e.g., "by plan#", "by recent activity")
        """
        self._sort_mode = mode
        self._update_display()

    def set_author_filter(self, label: str | None) -> None:
        """Set the author filter display label.

        Args:
            label: Author filter label (e.g., "all", "schrockn"), or None to hide
        """
        self._author_filter = label
        self._update_display()

    def _update_display(self) -> None:
        """Render the status bar content."""
        # Active operations take priority
        if self._operations:
            op_id = self._last_updated_op_id
            if op_id is not None and op_id in self._operations:
                op = self._operations[op_id]
            else:
                op_id = next(iter(self._operations))
                op = self._operations[op_id]

            if len(self._operations) == 1:
                display = f" {op.label}"
            else:
                display = f" [{len(self._operations)} ops] {op.label}"
            if op.progress:
                display += f" {op.progress}"
            self.update(display)
            return

        # Transient messages take second priority
        if self._message is not None:
            self.update(f" {self._message}")
            return

        parts: list[str] = []

        # Item count with view-specific noun
        parts.append(f"{self._plan_count} {self._noun}")

        # Author filter
        if self._author_filter is not None:
            parts.append(f"author: {self._author_filter}")

        # Sort mode
        if self._sort_mode:
            parts.append(f"sorted {self._sort_mode}")

        # Last update time with optional duration and timing breakdown
        if self._last_update:
            update_str = f"updated: {self._last_update}"
            if self._fetch_duration is not None:
                update_str += f" ({self._fetch_duration:.1f}s)"
            if self._fetch_timings is not None:
                update_str += f" {self._fetch_timings.summary()}"
            parts.append(update_str)

        # Refresh countdown
        if self._seconds_remaining > 0:
            parts.append(f"next: {self._seconds_remaining}s")

        # Key hints
        key_hints = (
            "1-3:views Enter:open /:filter a:users t:stack o:obj s:sort r:refresh q:quit ?:help"
        )
        parts.append(key_hints)

        self.update(" │ ".join(parts))
