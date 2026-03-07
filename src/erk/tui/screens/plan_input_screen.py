"""Modal screen for entering an incremental dispatch plan."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, TextArea


class PlanInputScreen(ModalScreen[str | None]):
    """Modal with a multiline text area for entering incremental dispatch plan markdown.

    Returns the stripped plan text on Ctrl+S, or None on Escape.
    Does NOT bind ``q`` -- the user needs to type ``q`` in plans.
    """

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Close"),
        Binding("ctrl+s", "submit_plan", "Submit", show=False),
    ]

    DEFAULT_CSS = """
    PlanInputScreen {
        align: center middle;
    }

    #plan-input-dialog {
        width: 90%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #plan-input-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    #plan-input-area {
        height: 32;
        margin: 0 2;
    }

    #plan-input-footer {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, *, pr_number: int) -> None:
        """Initialize with the PR number to display in the title.

        Args:
            pr_number: The PR number being dispatched against
        """
        super().__init__()
        self._pr_number = pr_number

    def compose(self) -> ComposeResult:
        """Create the plan input dialog."""
        with Vertical(id="plan-input-dialog"):
            yield Label(f"Dispatch plan to PR #{self._pr_number}", id="plan-input-title")
            yield TextArea(id="plan-input-area")
            yield Label("Ctrl+S to dispatch \u00b7 Esc to cancel", id="plan-input-footer")

    def on_mount(self) -> None:
        """Focus the text area on mount."""
        self.query_one("#plan-input-area", TextArea).focus()

    def action_submit_plan(self) -> None:
        """Handle Ctrl+S -- dismiss with stripped text, or None if empty."""
        text = self.query_one("#plan-input-area", TextArea).text.strip()
        self.dismiss(text if text else None)

    def action_dismiss_cancel(self) -> None:
        """Dismiss the screen with no action."""
        self.dismiss(None)
