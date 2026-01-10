"""Clickable link widget that opens a URL in the browser."""

from __future__ import annotations

from typing import Any

from rich.markup import escape as escape_markup
from textual.events import Click
from textual.widgets import Static


class ClickableLink(Static):
    """A clickable link widget that opens a URL in the browser."""

    DEFAULT_CSS = """
    ClickableLink {
        color: $primary;
        text-style: underline;
    }
    ClickableLink:hover {
        color: $primary-lighten-2;
    }
    """

    def __init__(self, text: str, url: str, **kwargs: Any) -> None:
        """Initialize clickable link.

        Args:
            text: Display text for the link
            url: URL to open when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(escape_markup(text), **kwargs)
        self._url = url

    def on_click(self, event: Click) -> None:
        """Open URL in browser when clicked."""
        event.stop()
        # Access browser through the app's provider (ErkDashApp)
        # Use getattr to avoid circular import isinstance issues
        app: Any = self.app
        provider = getattr(app, "_provider", None)
        if provider is not None:
            browser = getattr(provider, "browser", None)
            if browser is not None:
                browser.launch(self._url)
