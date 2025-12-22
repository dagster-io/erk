"""Main Textual application for JSONL viewer."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from erk.tui.jsonl_viewer.models import parse_jsonl_file
from erk.tui.jsonl_viewer.widgets import CustomListView, JsonlEntryItem


class JsonlViewerApp(App):
    """Interactive TUI for viewing JSONL files."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    DEFAULT_CSS = """
    JsonlViewerApp {
        background: $surface;
    }

    ListView {
        height: 1fr;
    }

    ListView > ListItem.--highlight {
        background: $primary-darken-2;
    }
    """

    def __init__(self, jsonl_path: Path) -> None:
        """Initialize with path to JSONL file.

        Args:
            jsonl_path: Path to the JSONL file to view
        """
        super().__init__()
        self._jsonl_path = jsonl_path
        self._entries = parse_jsonl_file(jsonl_path)

    def compose(self) -> ComposeResult:
        """Create application layout."""
        yield Header(show_clock=False)
        yield CustomListView(*[JsonlEntryItem(entry) for entry in self._entries])
        yield Footer()

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j key)."""
        list_view = self.query_one(CustomListView)
        list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k key)."""
        list_view = self.query_one(CustomListView)
        list_view.action_cursor_up()
