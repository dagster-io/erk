"""Browser launcher abstraction for testability.

This module provides an ABC for launching URLs in a browser to enable
testing without actually opening browser windows.
"""

from abc import ABC, abstractmethod


class BrowserLauncher(ABC):
    """Abstract interface for launching URLs in a browser."""

    @abstractmethod
    def launch(self, url: str) -> None:
        """Launch a URL in the default web browser.

        Args:
            url: The URL to open in the browser
        """
        ...
