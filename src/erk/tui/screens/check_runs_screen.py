"""Modal screen displaying failing CI check runs for a PR."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from erk.tui.formatting.ci_checks import format_check_runs
from erk_shared.gateway.github.types import PRCheckRun
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


class CheckRunsScreen(ModalScreen):
    """Modal screen displaying failing CI check runs."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    CheckRunsScreen {
        align: center middle;
    }

    #checks-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #checks-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #checks-title {
        text-style: bold;
        color: $primary;
    }

    #checks-summary {
        color: $text;
    }

    #checks-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #checks-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #checks-content {
        width: 100%;
    }

    #checks-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #checks-loading {
        color: $text-muted;
        text-style: italic;
    }

    #checks-empty {
        color: $text-muted;
        text-style: italic;
    }

    #checks-error {
        color: $error;
        text-style: italic;
    }

    #checks-summaries-loading {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        pr_number: int,
        full_title: str,
        passing_count: int,
        total_count: int,
    ) -> None:
        """Initialize with PR metadata and provider for async loading.

        Args:
            provider: Data provider for fetching check runs
            pr_number: The PR number to fetch check runs for
            full_title: The full plan title for display
            passing_count: Number of passing checks
            total_count: Total number of checks
        """
        super().__init__()
        self._provider = provider
        self._pr_number = pr_number
        self._full_title = full_title
        self._passing_count = passing_count
        self._total_count = total_count
        self._check_runs: list[PRCheckRun] = []

    def compose(self) -> ComposeResult:
        """Create the checks dialog content."""
        failing = self._total_count - self._passing_count
        with Vertical(id="checks-dialog"):
            with Vertical(id="checks-header"):
                yield Label(f"PR #{self._pr_number} Failing Checks", id="checks-title")
                yield Label(
                    f"{self._full_title}  ({failing} failing / {self._total_count} total)",
                    id="checks-summary",
                    markup=False,
                )

            yield Label("", id="checks-divider")

            with Container(id="checks-content-container"):
                yield Label("Loading check runs...", id="checks-loading")

            yield Label("Press Esc, q, or Space to close", id="checks-footer")

    def on_mount(self) -> None:
        """Fetch check runs when screen mounts."""
        self._fetch_check_runs()

    @work(thread=True)
    def _fetch_check_runs(self) -> None:
        """Fetch failing check runs in background thread."""
        check_runs: list[PRCheckRun] = []
        error: str | None = None

        try:
            check_runs = self._provider.fetch_check_runs(self._pr_number)
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_check_runs_loaded, check_runs, error)

    def _on_check_runs_loaded(self, check_runs: list[PRCheckRun], error: str | None) -> None:
        """Handle check runs loaded - update the display.

        Phase 1: show check runs immediately, then start Phase 2
        to fetch summaries in the background.

        Args:
            check_runs: The fetched check runs
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#checks-content-container", Container)

        # Remove the loading label
        container.query_one("#checks-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="checks-error"))
            return

        if not check_runs:
            container.mount(Label("(No failing checks found)", id="checks-empty"))
            return

        # Phase 1: display check runs without summaries
        self._check_runs = check_runs
        container.mount(
            Markdown(
                format_check_runs(check_runs, summaries=None),
                id="checks-content",
            )
        )

        # Phase 2: fetch summaries in background
        container.mount(Label("Loading failure summaries...", id="checks-summaries-loading"))
        self._fetch_summaries()

    @work(thread=True)
    def _fetch_summaries(self) -> None:
        """Fetch CI failure summaries in background thread."""
        summaries: dict[str, str] = {}

        try:
            summaries = self._provider.fetch_ci_summaries(self._pr_number)
        except Exception:
            # Summaries are best-effort; silently ignore failures
            pass

        self.app.call_from_thread(self._on_summaries_loaded, summaries)

    def _on_summaries_loaded(self, summaries: dict[str, str]) -> None:
        """Handle summaries loaded - update the display with enriched content.

        Args:
            summaries: Mapping of check name to summary text
        """
        container = self.query_one("#checks-content-container", Container)

        # Remove loading indicator
        loading = container.query("#checks-summaries-loading")
        for widget in loading:
            widget.remove()

        if not summaries:
            return

        # Update existing markdown content in-place (avoid remove/mount race)
        markdown = container.query_one("#checks-content", Markdown)
        markdown.update(format_check_runs(self._check_runs, summaries=summaries))
