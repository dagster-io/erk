"""Status bar widget for TUI dashboard."""

from textual.widgets import Static


class StatusBar(Static):
    """Footer status bar showing plan count, refresh status, and messages.

    Displays:
    - Plan count
    - Last update time
    - Time until next refresh
    - Action messages (e.g., command to copy)
    - Key bindings hint
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
        super().__init__()
        self._plan_count = 0
        self._seconds_remaining = 0
        self._last_update: str | None = None
        self._fetch_duration: float | None = None
        self._message: str | None = None
        self._sort_mode: str | None = None

    def set_plan_count(self, count: int) -> None:
        """Update the plan count display.

        Args:
            count: Number of plans currently displayed
        """
        self._plan_count = count
        self._update_display()

    def set_refresh_countdown(self, seconds: int) -> None:
        """Update the refresh countdown.

        Args:
            seconds: Seconds until next refresh
        """
        self._seconds_remaining = seconds
        self._update_display()

    def set_message(self, message: str | None) -> None:
        """Set or clear a status message.

        Args:
            message: Message to display, or None to clear
        """
        self._message = message
        self._update_display()

    def set_last_update(self, time_str: str, duration_secs: float | None = None) -> None:
        """Set the last update time.

        Args:
            time_str: Formatted time string (e.g., "14:30:45")
            duration_secs: Duration of the fetch in seconds, or None
        """
        self._last_update = time_str
        self._fetch_duration = duration_secs
        self._update_display()

    def set_sort_mode(self, mode: str) -> None:
        """Set the current sort mode display.

        Args:
            mode: Sort mode label (e.g., "by issue#", "by recent activity")
        """
        self._sort_mode = mode
        self._update_display()

    def _update_display(self) -> None:
        """Render the status bar content."""
        parts: list[str] = []

        # Plan count
        if self._plan_count == 1:
            parts.append("1 plan")
        else:
            parts.append(f"{self._plan_count} plans")

        # Sort mode
        if self._sort_mode:
            parts.append(f"sorted {self._sort_mode}")

        # Last update time with optional duration
        if self._last_update:
            update_str = f"updated: {self._last_update}"
            if self._fetch_duration is not None:
                update_str += f" ({self._fetch_duration:.1f}s)"
            parts.append(update_str)

        # Refresh countdown
        if self._seconds_remaining > 0:
            parts.append(f"next: {self._seconds_remaining}s")

        # Message
        if self._message:
            parts.append(self._message)

        # Key hints
        parts.append("Enter:open  p:PR  /:filter  s:sort  r:refresh  q:quit  ?:help")

        self.update(" │ ".join(parts))
