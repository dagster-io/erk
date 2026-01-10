"""Modal screen showing keyboard shortcuts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    .help-section {
        margin-top: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $primary;
    }

    .help-binding {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help dialog content."""
        with Vertical(id="help-dialog"):
            yield Label("erk dash - Keyboard Shortcuts", id="help-title")

            with Vertical(classes="help-section"):
                yield Label("Navigation", classes="help-section-title")
                yield Label("↑/k     Move cursor up", classes="help-binding")
                yield Label("↓/j     Move cursor down", classes="help-binding")
                yield Label("Home    Jump to first row", classes="help-binding")
                yield Label("End     Jump to last row", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Actions", classes="help-section-title")
                yield Label("Enter   View plan details", classes="help-binding")
                yield Label("Ctrl+P  Commands (opens detail modal)", classes="help-binding")
                yield Label("v       View plan text", classes="help-binding")
                yield Label("o       Open PR (or issue if no PR)", classes="help-binding")
                yield Label("p       Open PR in browser", classes="help-binding")
                yield Label("i       Show implement command", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Filter & Sort", classes="help-section-title")
                yield Label("/       Start filter mode", classes="help-binding")
                yield Label("Esc     Clear filter / exit filter", classes="help-binding")
                yield Label("Enter   Return focus to table", classes="help-binding")
                yield Label("s       Toggle sort mode", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("General", classes="help-section-title")
                yield Label("r       Refresh data", classes="help-binding")
                yield Label("?       Show this help", classes="help-binding")
                yield Label("q/Esc   Quit", classes="help-binding")

            yield Label("")
            yield Label("Press any key to close", id="help-footer")
