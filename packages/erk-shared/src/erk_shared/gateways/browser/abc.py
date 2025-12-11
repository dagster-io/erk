"""Browser launcher abstraction for testing.

This module provides an ABC for browser launch operations to enable
testing without actually opening browser windows.
"""

from abc import ABC, abstractmethod


class BrowserLauncher(ABC):
    """Abstract browser launcher for dependency injection."""

    @abstractmethod
    def launch(self, url: str) -> bool:
        """Launch a URL in the system browser.

        Args:
            url: URL to open in browser

        Returns:
            True if launch succeeded, False if browser unavailable
        """
        ...
