"""Widget for displaying live subprocess output in the TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Static


class CommandOutputPanel(Static):
    """Bottom panel showing live subprocess output.

    Displays streaming output from a subprocess with status indicator
    and dismiss hint after completion.
    """

    DEFAULT_CSS = """
    CommandOutputPanel {
        height: auto;
        max-height: 15;
        background: $surface-darken-1;
        border-top: solid $primary;
        padding: 0 1;
    }

    CommandOutputPanel #output-header {
        height: 1;
        color: $primary;
        text-style: bold;
    }

    CommandOutputPanel #output-log {
        height: auto;
        max-height: 10;
        scrollbar-gutter: stable;
    }

    CommandOutputPanel #output-status {
        height: 1;
        color: $text-muted;
    }

    CommandOutputPanel #output-status.success {
        color: #238636;
    }

    CommandOutputPanel #output-status.failure {
        color: #da3633;
    }
    """

    def __init__(self, title: str) -> None:
        """Initialize output panel.

        Args:
            title: Title to show at the top of the panel
        """
        super().__init__()
        self._title = title
        self._completed = False
        self._success = False

    @property
    def is_completed(self) -> bool:
        """Check if the command has completed."""
        return self._completed

    @property
    def succeeded(self) -> bool:
        """Check if the command succeeded."""
        return self._success

    def compose(self) -> ComposeResult:
        """Create panel content."""
        with Vertical():
            yield Static(f"[bold]{self._title}[/bold]", id="output-header")
            yield RichLog(id="output-log", highlight=True, markup=True)
            yield Static("Running...", id="output-status")

    def append_line(self, line: str, is_stderr: bool = False) -> None:
        """Add output line to the log.

        Args:
            line: The line of output to append
            is_stderr: If True, style as error output (red)
        """
        log = self.query_one("#output-log", RichLog)
        if is_stderr:
            log.write(f"[red]{line}[/red]")
        else:
            log.write(line)

    def set_completed(self, success: bool) -> None:
        """Mark command as complete and show dismiss hint.

        Args:
            success: Whether the command succeeded
        """
        self._completed = True
        self._success = success

        status = self.query_one("#output-status", Static)
        if success:
            status.update("✓ Complete - Press Esc to close")
            status.add_class("success")
        else:
            status.update("✗ Failed - Press Esc to close")
            status.add_class("failure")
