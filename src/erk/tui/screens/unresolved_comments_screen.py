"""Modal screen displaying unresolved PR review comments."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from erk_shared.gateway.github.types import PRReviewThread
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _format_threads(threads: list[PRReviewThread]) -> str:
    """Format review threads as markdown for display.

    Args:
        threads: List of unresolved PRReviewThread objects

    Returns:
        Markdown-formatted string with thread details
    """
    if not threads:
        return "*No unresolved comments*"

    parts: list[str] = []
    for thread in threads:
        line_suffix = f":{thread.line}" if thread.line is not None else ""
        header = f"### `{thread.path}{line_suffix}`"

        if thread.comments:
            first_comment = thread.comments[0]
            # Format: **author** · date
            date_part = first_comment.created_at[:10] if first_comment.created_at else ""
            meta = f"**{first_comment.author}** · {date_part}"

            reply_count = len(thread.comments) - 1
            if reply_count > 0:
                reply_note = f"\n\n*+ {reply_count} {'reply' if reply_count == 1 else 'replies'}*"
            else:
                reply_note = ""

            parts.append(f"{header}\n{meta}\n\n{first_comment.body}{reply_note}\n\n---")
        else:
            parts.append(f"{header}\n\n*(empty thread)*\n\n---")

    return "\n\n".join(parts)


class UnresolvedCommentsScreen(ModalScreen):
    """Modal screen displaying unresolved PR review comments."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    UnresolvedCommentsScreen {
        align: center middle;
    }

    #comments-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #comments-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #comments-title {
        text-style: bold;
        color: $primary;
    }

    #comments-summary {
        color: $text;
    }

    #comments-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #comments-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #comments-content {
        width: 100%;
    }

    #comments-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #comments-loading {
        color: $text-muted;
        text-style: italic;
    }

    #comments-empty {
        color: $text-muted;
        text-style: italic;
    }

    #comments-error {
        color: $error;
        text-style: italic;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        pr_number: int,
        full_title: str,
        resolved_count: int,
        total_count: int,
    ) -> None:
        """Initialize with PR metadata and provider for async loading.

        Args:
            provider: Data provider for fetching review threads
            pr_number: The PR number to fetch comments for
            full_title: The full plan title for display
            resolved_count: Number of resolved comment threads
            total_count: Total number of comment threads
        """
        super().__init__()
        self._provider = provider
        self._pr_number = pr_number
        self._full_title = full_title
        self._resolved_count = resolved_count
        self._total_count = total_count

    def compose(self) -> ComposeResult:
        """Create the comments dialog content."""
        unresolved = self._total_count - self._resolved_count
        with Vertical(id="comments-dialog"):
            with Vertical(id="comments-header"):
                yield Label(f"PR #{self._pr_number} Comments", id="comments-title")
                yield Label(
                    f"{self._full_title}  ({unresolved} unresolved / {self._total_count} total)",
                    id="comments-summary",
                    markup=False,
                )

            yield Label("", id="comments-divider")

            with Container(id="comments-content-container"):
                yield Label("Loading comments...", id="comments-loading")

            yield Label("Press Esc, q, or Space to close", id="comments-footer")

    def on_mount(self) -> None:
        """Fetch comments when screen mounts."""
        self._fetch_comments()

    @work(thread=True)
    def _fetch_comments(self) -> None:
        """Fetch unresolved comments in background thread."""
        threads: list[PRReviewThread] = []
        error: str | None = None

        # Error boundary: catch all exceptions from API operations to display
        # them in the UI rather than crashing the TUI.
        try:
            threads = self._provider.fetch_unresolved_comments(self._pr_number)
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_comments_loaded, threads, error)

    def _on_comments_loaded(self, threads: list[PRReviewThread], error: str | None) -> None:
        """Handle comments loaded - update the display.

        Args:
            threads: The fetched review threads
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#comments-content-container", Container)

        # Remove the loading label
        container.query_one("#comments-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="comments-error"))
        elif threads:
            container.mount(Markdown(_format_threads(threads), id="comments-content"))
        else:
            container.mount(Label("(No unresolved comments found)", id="comments-empty"))
