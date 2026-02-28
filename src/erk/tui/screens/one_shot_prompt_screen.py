"""Modal screen for entering a one-shot prompt."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class OneShotPromptScreen(ModalScreen[str | None]):
    """Modal with a text input for dispatching a one-shot prompt.

    Returns the stripped prompt text on Enter, or None on Escape.
    Does NOT bind ``q`` — the user needs to type ``q`` in prompts.
    """

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Close"),
    ]

    DEFAULT_CSS = """
    OneShotPromptScreen {
        align: center middle;
    }

    #one-shot-dialog {
        width: 72;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #one-shot-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    #one-shot-input {
        margin: 0 2;
    }

    #one-shot-footer {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the prompt dialog."""
        with Vertical(id="one-shot-dialog"):
            yield Label("One-Shot Prompt", id="one-shot-title")
            yield Input(id="one-shot-input", placeholder="Describe the task...")
            yield Label("Enter to dispatch · Esc to cancel", id="one-shot-footer")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one("#one-shot-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter — dismiss with stripped text, or None if empty."""
        text = event.value.strip()
        self.dismiss(text if text else None)

    def action_dismiss_cancel(self) -> None:
        """Dismiss the screen with no action."""
        self.dismiss(None)
