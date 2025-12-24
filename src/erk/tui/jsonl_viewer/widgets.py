"""Widgets for JSONL viewer."""

import json

from rich.markup import escape as escape_markup
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

from erk.tui.jsonl_viewer.models import JsonlEntry, format_entry_detail, format_summary


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

    JsonlEntryItem.selected {
        background: $accent;
    }

    JsonlEntryItem.selected .entry-summary {
        color: $text;
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
        # Use markup=False to avoid Rich interpreting brackets as markup tags
        pretty_json = json.dumps(self._entry.parsed, indent=2)
        with Vertical(classes="json-detail"):
            yield Static(pretty_json, markup=False)

    def toggle_expand(self) -> None:
        """Toggle expand/collapse state."""
        self._expanded = not self._expanded
        if self._expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        # Ensure the widget is updated
        self.refresh()

    def set_expanded(self, expanded: bool) -> None:
        """Set expand state explicitly.

        Args:
            expanded: Whether to expand (True) or collapse (False)
        """
        self._expanded = expanded
        if expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        self.refresh()

    def is_expanded(self) -> bool:
        """Return current expanded state."""
        return self._expanded

    def update_format(self, formatted: bool) -> None:
        """Update the JSON detail display format.

        Args:
            formatted: If True, use YAML-like format. If False, use raw JSON.
        """
        detail_container = self.query_one(".json-detail", Vertical)
        static = detail_container.query_one(Static)
        content = format_entry_detail(self._entry, formatted=formatted)
        # No escape_markup needed - Static widget has markup=False
        static.update(content)


class CustomListView(ListView):
    """Custom ListView with expand/collapse keybinding."""

    BINDINGS = [
        Binding("enter", "toggle_expand", "Expand/Collapse"),
        Binding("f", "toggle_format", "Format"),
    ]

    def __init__(self, *children: ListItem) -> None:
        """Initialize with format and expand mode state.

        Args:
            children: List items to include in the view
        """
        super().__init__(*children)
        self._formatted_mode = True
        self._expand_mode = False
        self._expanded_item: JsonlEntryItem | None = None

    def action_toggle_expand(self) -> None:
        """Toggle expand/collapse for selected entry."""
        highlighted = self.highlighted_child
        if isinstance(highlighted, JsonlEntryItem):
            highlighted.toggle_expand()
            # Track expand mode
            self._expand_mode = highlighted.is_expanded()
            self._expanded_item = highlighted if self._expand_mode else None

    def action_toggle_format(self) -> None:
        """Toggle format mode between formatted and raw JSON."""
        self._formatted_mode = not self._formatted_mode
        # Update all items with new format
        for child in self.children:
            if isinstance(child, JsonlEntryItem):
                child.update_format(self._formatted_mode)

    def watch_index(self, old_index: int | None, new_index: int | None) -> None:
        """Handle index changes for sticky expand mode and selection styling.

        Args:
            old_index: Previous highlighted index (None if no previous selection)
            new_index: New highlighted index (None if no selection)
        """
        # Update selection styling
        if old_index is not None and old_index >= 0 and old_index < len(self.children):
            old_child = self.children[old_index]
            if isinstance(old_child, JsonlEntryItem):
                old_child.remove_class("selected")

        if new_index is not None and new_index >= 0 and new_index < len(self.children):
            new_child = self.children[new_index]
            if isinstance(new_child, JsonlEntryItem):
                new_child.add_class("selected")

                # Sticky expand mode: maintain expand state when navigating
                if self._expand_mode and self._expanded_item is not None:
                    # Collapse previous expanded item
                    self._expanded_item.set_expanded(False)
                    # Expand new item
                    new_child.set_expanded(True)
                    self._expanded_item = new_child

    def _on_list_item__child_clicked(self, event: ListItem._ChildClicked) -> None:
        """Disable mouse clicks for item selection.

        We want keyboard-only navigation for this viewer.
        """
        event.prevent_default()
        event.stop()
