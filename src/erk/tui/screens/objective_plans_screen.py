"""Modal screen displaying plans associated with an objective."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from erk.tui.data.types import PlanRowData
from erk_shared.gateway.github.metadata.roadmap import parse_roadmap
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


def _extract_plan_ids_from_roadmap(body: str) -> set[int]:
    """Extract plan IDs from roadmap nodes in the objective body.

    Parses the roadmap frontmatter and collects PR references (e.g., "#8070")
    from each node, converting them to integer plan IDs.

    Args:
        body: The objective issue body containing roadmap metadata

    Returns:
        Set of plan issue numbers referenced in the roadmap
    """
    phases, _errors = parse_roadmap(body)
    plan_ids: set[int] = set()
    for phase in phases:
        for node in phase.nodes:
            if node.pr is not None:
                pr_str = node.pr.lstrip("#")
                if pr_str.isdigit():
                    plan_ids.add(int(pr_str))
    return plan_ids


def _format_plan_rows(plans: list[PlanRowData]) -> list[str]:
    """Format plan rows as display strings.

    Args:
        plans: List of PlanRowData objects to format

    Returns:
        List of formatted strings, one per plan
    """
    lines: list[str] = []
    for plan in plans:
        pr_part = f"  PR {plan.pr_display}" if plan.pr_number is not None else ""
        state_part = f"  {plan.pr_state}" if plan.pr_state is not None else ""
        lines.append(f"#{plan.plan_id}  {plan.full_title}{pr_part}{state_part}")
    return lines


class ObjectivePlansScreen(ModalScreen):
    """Modal screen displaying plans associated with an objective."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    ObjectivePlansScreen {
        align: center middle;
    }

    #obj-plans-dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #obj-plans-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #obj-plans-title {
        text-style: bold;
        color: $primary;
    }

    #obj-plans-summary {
        color: $text;
    }

    #obj-plans-divider {
        height: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #obj-plans-content-container {
        height: 1fr;
        overflow-y: auto;
    }

    #obj-plans-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    #obj-plans-loading {
        color: $text-muted;
        text-style: italic;
    }

    #obj-plans-empty {
        color: $text-muted;
        text-style: italic;
    }

    #obj-plans-error {
        color: $error;
        text-style: italic;
    }

    .obj-plan-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        objective_id: int,
        objective_title: str,
        progress_display: str,
        objective_body: str,
    ) -> None:
        """Initialize with objective metadata and provider for async loading.

        Args:
            provider: Data provider for fetching plans
            objective_id: The objective issue number
            objective_title: The objective title for display
            progress_display: Progress display string (e.g., "3/7")
            objective_body: The raw objective issue body (for roadmap extraction)
        """
        super().__init__()
        self._provider = provider
        self._objective_id = objective_id
        self._objective_title = objective_title
        self._progress_display = progress_display
        self._objective_body = objective_body

    def compose(self) -> ComposeResult:
        """Create the objective plans dialog content."""
        with Vertical(id="obj-plans-dialog"):
            with Vertical(id="obj-plans-header"):
                yield Label(
                    f"Objective #{self._objective_id} Plans",
                    id="obj-plans-title",
                )
                yield Label(
                    f"{self._objective_title}  ({self._progress_display})",
                    id="obj-plans-summary",
                    markup=False,
                )

            yield Label("", id="obj-plans-divider")

            with Container(id="obj-plans-content-container"):
                yield Label("Loading plans...", id="obj-plans-loading")

            yield Label("Press Esc, q, or Space to close", id="obj-plans-footer")

    def on_mount(self) -> None:
        """Fetch plans when screen mounts."""
        self._fetch_plans()

    @work(thread=True)
    def _fetch_plans(self) -> None:
        """Fetch plans for this objective in background thread."""
        plans: list[PlanRowData] = []
        error: str | None = None

        # Error boundary: catch all exceptions from API operations to display
        # them in the UI rather than crashing the TUI.
        try:
            roadmap_plan_ids = _extract_plan_ids_from_roadmap(self._objective_body)
            if roadmap_plan_ids:
                plans = self._provider.fetch_plans_by_ids(roadmap_plan_ids)
            else:
                plans = self._provider.fetch_plans_for_objective(self._objective_id)
        except Exception as e:
            error = str(e)

        self.app.call_from_thread(self._on_plans_loaded, plans, error)

    def _on_plans_loaded(self, plans: list[PlanRowData], error: str | None) -> None:
        """Handle plans loaded - update the display.

        Args:
            plans: The fetched plan rows
            error: Error message if fetch failed, or None
        """
        container = self.query_one("#obj-plans-content-container", Container)

        # Remove the loading label
        container.query_one("#obj-plans-loading", Label).remove()

        if error is not None:
            container.mount(Label(f"Error: {error}", id="obj-plans-error"))
        elif plans:
            for line in _format_plan_rows(plans):
                container.mount(Label(line, classes="obj-plan-row", markup=False))
        else:
            container.mount(Label("(No plans found for this objective)", id="obj-plans-empty"))
