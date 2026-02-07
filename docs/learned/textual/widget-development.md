---
title: Textual Widget Development Guide
read_when:
  - "creating Textual widgets"
  - "adding ModalScreen dialogs"
  - "implementing keyboard bindings"
  - "writing Textual CSS styles"
---

# Textual Widget Development

## ModalScreen Pattern

```python
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label

class ConfirmationDialog(ModalScreen[bool]):
    """Modal that returns a boolean result."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmationDialog {
        align: center middle;
    }
    #dialog {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._message)
            yield Label("[y] Yes  [n] No")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
```

## Binding Patterns

```python
BINDINGS = [
    # Basic key
    Binding("q", "quit", "Quit"),

    # Shift+key (use capital letter)
    Binding("S", "submit", "Submit!", key_display="Shift+S"),

    # Hidden binding (not shown in footer)
    Binding("j", "down", "Down", show=False),

    # Named keys
    Binding("escape", "cancel", "Cancel"),
    Binding("space", "select", "Select"),
    Binding("slash", "filter", "Filter", key_display="/"),

    # Number keys
    Binding("1", "option_one", "Option 1"),
    Binding("2", "option_two", "Option 2"),
]
```

## Action Methods

Bindings automatically call `action_{name}()`:

```python
def action_quit(self) -> None:
    """Called when 'q' is pressed."""
    self.app.exit()

def action_submit(self) -> None:
    """Called when Shift+S is pressed."""
    # Show confirmation dialog with callback
    self.app.push_screen(
        ConfirmationDialog("Confirm?"),
        callback=self._on_confirmed,
    )

def _on_confirmed(self, result: bool | None) -> None:
    """Callback receives T | None (None if dismissed without result)."""
    if result is True:
        # User confirmed
        pass
```

## CSS in Widgets

Use `DEFAULT_CSS` class attribute for widget-specific styles:

```python
DEFAULT_CSS = """
MyWidget {
    align: center middle;
}
.section-header {
    color: $text-muted;
    text-style: bold italic;
    margin-top: 1;
}
.status-badge {
    padding: 0 1;
    background: $primary;
}
.info-row {
    layout: horizontal;
    height: 1;
}
.command-key {
    color: $accent;
    width: 4;
}
"""
```

## compose() Method

```python
def compose(self) -> ComposeResult:
    with Vertical(id="container"):
        yield Label("Header", id="header")

        # Conditional rendering
        if self._show_details:
            with Container(classes="details"):
                yield Label("Detail 1")
                yield Label("Detail 2")

        yield Label("Footer", id="footer")
```

## Common Widget Types

```python
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Label, Static, Input, Button
```

- `Label` - Simple text display
- `Static` - Text with markup support
- `Container` - Generic container (horizontal by default)
- `Vertical` - Vertical layout container
- `Horizontal` - Horizontal layout container
- `Input` - Text input field

## Accessing App from Widget

```python
# From within a widget or screen
def some_method(self) -> None:
    # Generic app access
    self.app.exit()

    # Type-safe access to specific app class
    from erk.tui.app import ErkDashApp
    app = self.app
    if isinstance(app, ErkDashApp):
        app.exit_command = "some command"
```

## Notifications

```python
# Show a brief notification toast
self.notify("Copied: erk implement 123", timeout=2)
```

## RichLog for Streaming Output

Use `RichLog` for scrollable, auto-updating output displays:

```python
from textual.widgets import RichLog

class CommandOutputPanel(Static):
    """Panel showing live command output."""

    def compose(self) -> ComposeResult:
        yield RichLog(id="output", wrap=True, markup=True)

    def append_line(self, line: str) -> None:
        """Add a line to the output log."""
        log = self.query_one("#output", RichLog)
        log.write(line)
```

`RichLog` features:

- Auto-scrolling to bottom as content is added
- Rich markup support for colored output
- Efficient for high-frequency updates
- `wrap=True` enables word wrapping

## Example Files

- `src/erk/tui/app.py` - Main app with ModalScreens (HelpScreen, PlanDetailScreen, ConfirmationDialog)
- `src/erk/tui/widgets/` - Reusable widget components
