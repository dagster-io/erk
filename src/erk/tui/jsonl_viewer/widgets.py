"""Widgets for JSONL viewer."""

import json

from rich.markup import escape as escape_markup
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

from erk.tui.jsonl_viewer.models import JsonlEntry, format_summary


class JsonlEntryItem(ListItem):
    """Expandable JSONL entry with summary and JSON detail."""

    DEFAULT_CSS = """
    JsonlEntryItem {
        height: auto;
        padding: 0 1;
    }

    JsonlEntryItem .entry-summary {
        height: 1;
    }

    JsonlEntryItem .entry-summary-user {
        color: #58a6ff;
    }

    JsonlEntryItem .entry-summary-assistant {
        color: #7ee787;
    }

    JsonlEntryItem .entry-summary-tool-result {
        color: #ffa657;
    }

    JsonlEntryItem .entry-summary-other {
        color: $text-muted;
    }

    JsonlEntryItem .json-detail {
        display: none;
        padding: 1;
        background: $surface-darken-1;
        overflow-x: auto;
    }

    JsonlEntryItem.expanded .json-detail {
        display: block;
    }
    """

    def __init__(self, entry: JsonlEntry) -> None:
        """Initialize with JSONL entry.

        Args:
            entry: The JSONL entry to display
        """
        super().__init__()
        self._entry = entry
        self._expanded = False

    def compose(self) -> ComposeResult:
        """Create widget content."""
        summary = format_summary(self._entry)

        # Determine style class based on entry type
        entry_type = self._entry.entry_type
        if entry_type == "user":
            style_class = "entry-summary entry-summary-user"
        elif entry_type == "assistant":
            style_class = "entry-summary entry-summary-assistant"
        elif entry_type == "tool_result":
            style_class = "entry-summary entry-summary-tool-result"
        else:
            style_class = "entry-summary entry-summary-other"

        yield Label(escape_markup(summary), classes=style_class)

        # Pretty-printed JSON detail (hidden by default)
        pretty_json = json.dumps(self._entry.parsed, indent=2)
        with Vertical(classes="json-detail"):
            yield Static(escape_markup(pretty_json))

    def toggle_expand(self) -> None:
        """Toggle expand/collapse state."""
        self._expanded = not self._expanded
        if self._expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        # Ensure the widget is updated
        self.refresh()


class CustomListView(ListView):
    """Custom ListView with expand/collapse keybinding."""

    BINDINGS = [
        Binding("enter", "toggle_expand", "Expand/Collapse"),
    ]

    def action_toggle_expand(self) -> None:
        """Toggle expand/collapse for selected entry."""
        highlighted = self.highlighted_child
        if isinstance(highlighted, JsonlEntryItem):
            highlighted.toggle_expand()
