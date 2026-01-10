"""Copyable label widget that copies text to clipboard when clicked."""

from __future__ import annotations

from typing import Any

from textual.events import Click
from textual.widgets import Static


class CopyableLabel(Static):
    """A label that copies text to clipboard when clicked, styled with orange/accent color."""

    DEFAULT_CSS = """
    CopyableLabel {
        color: $accent;
    }
    CopyableLabel:hover {
        color: $accent-lighten-1;
        text-style: bold;
    }
    """

    def __init__(self, label: str, text_to_copy: str, **kwargs: Any) -> None:
        """Initialize copyable label.

        Args:
            label: Display text for the label (e.g., "[1]" or "erk pr co 2022")
            text_to_copy: Text to copy to clipboard when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(label, **kwargs)
        self._text_to_copy = text_to_copy
        self._original_label = label

    def on_click(self, event: Click) -> None:
        """Copy text to clipboard when clicked."""
        event.stop()
        success = self._copy_to_clipboard()
        if success:
            self.update("Copied!")
            self.set_timer(1.5, lambda: self.update(self._original_label))

    def _copy_to_clipboard(self) -> bool:
        """Copy text to clipboard, finding the clipboard interface.

        Returns:
            True if copy succeeded, False otherwise.
        """
        # Access clipboard through the app's provider (ErkDashApp)
        # Use getattr to avoid circular import isinstance issues
        app: Any = self.app
        provider = getattr(app, "_provider", None)
        if provider is not None:
            clipboard = getattr(provider, "clipboard", None)
            if clipboard is not None:
                return clipboard.copy(self._text_to_copy)
        return False
