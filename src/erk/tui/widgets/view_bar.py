"""View bar widget for TUI dashboard."""

from __future__ import annotations

from rich.text import Text
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

from erk.tui.views.types import VIEW_CONFIGS, ViewMode


def _build_view_bar_content(
    *,
    active_view: ViewMode,
    plans_display_name: str,
) -> tuple[Text, list[tuple[int, int, ViewMode]]]:
    """Build view bar text and tab regions.

    Returns:
        Tuple of (styled Rich Text, list of (start_x, end_x, ViewMode) regions)
    """
    text = Text()
    tab_regions: list[tuple[int, int, ViewMode]] = []
    x = 0
    for i, config in enumerate(VIEW_CONFIGS):
        if i > 0:
            text.append("  ")
            x += 2
        if config.mode == ViewMode.PLANS:
            display_name = plans_display_name
        else:
            display_name = config.display_name
        label = f"{config.key_hint}:{display_name}"
        tab_regions.append((x, x + len(label), config.mode))
        if config.mode == active_view:
            text.append(label, style="bold white")
        else:
            text.append(label, style="dim")
        x += len(label)
    return text, tab_regions


class ViewBar(Static):
    """Top bar showing available views with the active view highlighted.

    Renders: 1:Plans  2:Learn  3:Objectives
    Active view is bold white, inactive views are dimmed.
    Tabs are clickable to switch views.
    """

    class ViewTabClicked(Message):
        """Posted when user clicks a tab label in the view bar."""

        def __init__(self, view_mode: ViewMode) -> None:
            super().__init__()
            self.view_mode = view_mode

    DEFAULT_CSS = """
    ViewBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, *, active_view: ViewMode, plans_display_name: str) -> None:
        """Initialize the view bar.

        Args:
            active_view: The currently active view mode
            plans_display_name: Display label for the Plans view (e.g., "Plans" or "Planned PRs")
        """
        super().__init__()
        self._active_view = active_view
        self._plans_display_name = plans_display_name
        self._tab_regions: list[tuple[int, int, ViewMode]] = []

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
        text, tab_regions = _build_view_bar_content(
            active_view=self._active_view,
            plans_display_name=self._plans_display_name,
        )
        self._tab_regions = tab_regions
        self.update(text)

    def on_click(self, event: Click) -> None:
        """Handle click events on tab labels.

        Computes content-relative x by subtracting the 1-char left padding,
        then finds which tab region contains the click.

        Args:
            event: Click event from Textual
        """
        # padding: 0 1 means 1 char left padding
        content_x = event.x - 1
        for start_x, end_x, view_mode in self._tab_regions:
            if start_x <= content_x < end_x:
                self.post_message(self.ViewTabClicked(view_mode))
                event.stop()
                return
