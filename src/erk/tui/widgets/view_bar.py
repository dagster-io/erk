"""View bar widget for TUI dashboard."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from erk.tui.views.types import VIEW_CONFIGS, ViewMode


class ViewBar(Static):
    """Top bar showing available views with the active view highlighted.

    Renders: 1:Plans  2:Learn  3:Objectives
    Active view is bold white, inactive views are dimmed.
    """

    DEFAULT_CSS = """
    ViewBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, *, active_view: ViewMode) -> None:
        """Initialize the view bar.

        Args:
            active_view: The currently active view mode
        """
        super().__init__()
        self._active_view = active_view

    def on_mount(self) -> None:
        """Render the view bar on mount."""
        self._refresh_display()

    def set_active_view(self, mode: ViewMode) -> None:
        """Update the active view and re-render.

        Args:
            mode: The new active view mode
        """
        self._active_view = mode
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Render the view bar content with styled text."""
        text = Text()
        for i, config in enumerate(VIEW_CONFIGS):
            if i > 0:
                text.append("  ")
            label = f"{config.key_hint}:{config.display_name}"
            if config.mode == self._active_view:
                text.append(label, style="bold white")
            else:
                text.append(label, style="dim")
        self.update(text)
