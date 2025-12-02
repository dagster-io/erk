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

        # Note: pyperclip.is_available() returns False until first copy/paste call
        # (lazy initialization), so we try the operation and catch exceptions instead
        try:
            pyperclip.copy(text)
            return True
        except pyperclip.PyperclipException:
            return False
