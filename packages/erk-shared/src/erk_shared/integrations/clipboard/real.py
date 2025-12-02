"""Real Clipboard implementation using pyperclip.

RealClipboard provides cross-platform clipboard access using pyperclip,
which handles xclip/xsel on Linux, pbcopy on macOS, etc.
"""

from erk_shared.integrations.clipboard.abc import Clipboard


class RealClipboard(Clipboard):
    """Production implementation using pyperclip for clipboard access."""

    def copy(self, text: str) -> bool:
        """Copy text to clipboard using pyperclip.

        Args:
            text: Text to copy to clipboard

        Returns:
            True if copy succeeded, False if clipboard unavailable
            (e.g., in headless/SSH environments)
        """
        # Inline import: pyperclip is only needed for real clipboard operations
        # and may not be available in all environments
        import pyperclip

        if not pyperclip.is_available():
            return False
        pyperclip.copy(text)
        return True
