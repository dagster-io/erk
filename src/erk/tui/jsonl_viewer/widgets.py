"""Widgets for JSONL viewer."""

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

    JsonlEntryItem > .entry-summary {
        height: 1;
    }

    JsonlEntryItem.selected > .entry-summary {
        background: $secondary;
    }

    JsonlEntryItem > .entry-summary-user {
        color: #58a6ff;
    }

    JsonlEntryItem > .entry-summary-assistant {
        color: #7ee787;
    }

    JsonlEntryItem > .entry-summary-tool-result {
        color: #ffa657;
    }

    JsonlEntryItem > .entry-summary-other {
        color: $text-muted;
    }

    JsonlEntryItem > .json-detail {
        display: none;
        padding: 1;
        background: $surface-darken-1;
        overflow-x: auto;
    }

    JsonlEntryItem.expanded > .json-detail {
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
        self._detail_widget: Static | None = None

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

        # Pretty-printed JSON detail (hidden by default, starts in raw mode)
        detail_text = format_entry_detail(self._entry, formatted=False)
        with Vertical(classes="json-detail"):
            self._detail_widget = Static(detail_text, markup=False)
            yield self._detail_widget

    def set_expanded(self, expanded: bool) -> None:
        """Set the expanded state of this entry.

        Args:
            expanded: If True, show detail; if False, hide detail
        """
        if expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        self.refresh()

    def is_expanded(self) -> bool:
        """Check if this entry is expanded."""
        return self.has_class("expanded")

    def update_format(self, formatted: bool) -> None:
        """Update the detail display with the given format mode.

        Args:
            formatted: If True, use markdown mode; if False, use raw JSON
        """
        if self._detail_widget is not None:
            detail_text = format_entry_detail(self._entry, formatted)
            self._detail_widget.update(detail_text)
        self.refresh()


class CustomListView(ListView):
    """Custom ListView with single-expanded entry and global format mode.

    Mouse interaction is disabled - keyboard navigation only.
    """

    DEFAULT_CSS = """
    CustomListView > JsonlEntryItem:hover {
        background: transparent;
    }
    """

    BINDINGS = [
        Binding("enter", "toggle_expand", "Expand/Collapse"),
        Binding("f", "toggle_format", "Format"),
    ]

    def __init__(self, *children: ListItem) -> None:
        """Initialize with global format mode state.

        Args:
            children: Child ListItem widgets to display
        """
        super().__init__(*children)
        self._formatted_mode = False
        self._expand_mode = False  # Sticky: whether to expand on navigation
        self._expanded_item: JsonlEntryItem | None = None

    def _on_list_item__child_clicked(self, event: ListItem._ChildClicked) -> None:
        """Disable mouse click selection - keyboard only."""
        event.prevent_default()
        event.stop()

    def watch_index(self, old_index: int | None, new_index: int | None) -> None:
        """Watch for index changes to handle selection and expand state."""
        # Remove selection from old item
        if old_index is not None and old_index < len(self.children):
            old_item = self.children[old_index]
            if isinstance(old_item, JsonlEntryItem):
                old_item.remove_class("selected")

        # Collapse the previously expanded item
        if self._expanded_item is not None:
            self._expanded_item.set_expanded(False)
            self._expanded_item = None

        # Add selection to new item
        if new_index is not None:
            highlighted = self.highlighted_child
            if isinstance(highlighted, JsonlEntryItem):
                highlighted.add_class("selected")
                # Only expand if in expand mode
                if self._expand_mode:
                    highlighted.update_format(self._formatted_mode)
                    highlighted.set_expanded(True)
                    self._expanded_item = highlighted

    def action_toggle_expand(self) -> None:
        """Toggle expand/collapse for selected entry."""
        highlighted = self.highlighted_child
        if isinstance(highlighted, JsonlEntryItem):
            if highlighted.is_expanded():
                # Collapsing: turn off expand mode
                highlighted.set_expanded(False)
                self._expanded_item = None
                self._expand_mode = False
            else:
                # Expanding: turn on expand mode
                # Collapse any other expanded item first
                if self._expanded_item is not None and self._expanded_item != highlighted:
                    self._expanded_item.set_expanded(False)
                highlighted.update_format(self._formatted_mode)
                highlighted.set_expanded(True)
                self._expanded_item = highlighted
                self._expand_mode = True

    def action_toggle_format(self) -> None:
        """Toggle global format mode and update expanded entry."""
        self._formatted_mode = not self._formatted_mode
        # Update the currently expanded item with new format
        if self._expanded_item is not None:
            self._expanded_item.update_format(self._formatted_mode)
