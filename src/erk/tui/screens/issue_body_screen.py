"""Modal screen displaying the full plan text fetched on-demand."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from erk.tui.data.provider import PlanDataProvider


class IssueBodyScreen(ModalScreen):
    """Modal screen displaying the full plan text fetched on-demand."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    IssueBodyScreen {
        align: center middle;
    }

    #body-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #body-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #body-plan-number {
        text-style: bold;
        color: $primary;
    }

    #body-title {
        color: $text;
    }

    #body-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #body-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #body-content {
        width: 100%;
    }

    #body-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #body-empty {
        color: $text-muted;
        text-style: italic;
    }

    #body-loading {
        color: $text-muted;
        text-style: italic;
    }

    #body-error {
        color: $error;
        text-style: italic;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        issue_number: int,
        issue_body: str,
        full_title: str,
    ) -> None:
        """Initialize with plan metadata and provider for async loading.

        Args:
            provider: Data provider for fetching plan content
            issue_number: The GitHub issue number
            issue_body: The issue body (contains metadata with comment ID)
            full_title: The full plan title for display
        """
        super().__init__()
        self._provider = provider
        self._issue_number = issue_number
        self._issue_body = issue_body
        self._full_title = full_title
        self._content: str | None = None
        self._error: str | None = None
        self._loading = True

    def compose(self) -> ComposeResult:
        """Create the issue body dialog content."""
        with Vertical(id="body-dialog"):
            # Header: Plan number + title
            with Vertical(id="body-header"):
                yield Label(f"Plan #{self._issue_number}", id="body-plan-number")
                yield Label(self._full_title, id="body-title", markup=False)

            # Divider
            yield Label("", id="body-divider")

            # Body content in scrollable container - starts with loading state
            with Container(id="body-content-container"):
                yield Label("Loading plan content...", id="body-loading")

            yield Label("Press Esc, q, or Space to close", id="body-footer")

    def on_mount(self) -> None:
        """Fetch plan content when screen mounts."""
        self._fetch_content()

    @work(thread=True)
    def _fetch_content(self) -> None:
        """Fetch plan content in background thread."""
        content: str | None = None
        error: str | None = None

        # Error boundary: catch all exceptions from HTTP operations to display
        # them in the UI rather than crashing the TUI.
        try:
            content = self._provider.fetch_plan_content(self._issue_number, self._issue_body)
        except Exception as e:
            error = str(e)

        # Update UI on main thread
        self.app.call_from_thread(self._on_content_loaded, content, error)

    def _on_content_loaded(self, content: str | None, error: str | None) -> None:
        """Handle content loaded - update the display.

        Args:
            content: The fetched plan content, or None if not found
            error: Error message if fetch failed, or None
        """
        self._loading = False
        self._content = content
        self._error = error

        # Get the container and replace its content
        container = self.query_one("#body-content-container", Container)

        # Remove the loading label
        loading_label = container.query_one("#body-loading", Label)
        loading_label.remove()

        # Add the appropriate content
        if error is not None:
            container.mount(Label(f"Error: {error}", id="body-error"))
        elif content:
            container.mount(Markdown(content, id="body-content"))
        else:
            container.mount(Label("(No plan content found)", id="body-empty"))
