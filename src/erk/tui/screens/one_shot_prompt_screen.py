"""Modal screen for entering a one-shot prompt."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, TextArea


class OneShotPromptScreen(ModalScreen[str | None]):
    """Modal with a multiline text area for dispatching a one-shot prompt.

    Returns the stripped prompt text on Ctrl+Enter, or None on Escape.
    Does NOT bind ``q`` — the user needs to type ``q`` in prompts.
    """

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Close"),
        Binding("ctrl+enter", "submit_prompt", "Submit", show=False),
    ]

    DEFAULT_CSS = """
    OneShotPromptScreen {
        align: center middle;
    }

    #one-shot-dialog {
        width: 90%;
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
        height: 32;
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
            yield TextArea(id="one-shot-input")
            yield Label("Ctrl+Enter to dispatch · Esc to cancel", id="one-shot-footer")

    def on_mount(self) -> None:
        """Focus the text area on mount."""
        self.query_one("#one-shot-input", TextArea).focus()

    def action_submit_prompt(self) -> None:
        """Handle Ctrl+Enter — dismiss with stripped text, or None if empty."""
        text = self.query_one("#one-shot-input", TextArea).text.strip()
        self.dismiss(text if text else None)

    def action_dismiss_cancel(self) -> None:
        """Dismiss the screen with no action."""
        self.dismiss(None)
