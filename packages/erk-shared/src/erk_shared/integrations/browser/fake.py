"""Fake BrowserLauncher implementation for testing.

FakeBrowserLauncher is an in-memory implementation that captures launched URLs
without actually opening browser windows, enabling fast and predictable tests.
"""

from erk_shared.integrations.browser.abc import BrowserLauncher


class FakeBrowserLauncher(BrowserLauncher):
    """In-memory fake that captures URLs without opening a browser.

    This class has NO public setup methods. All state is captured during
    execution for test assertions.
    """

    def __init__(self) -> None:
        """Create FakeBrowserLauncher with empty URL tracking."""
        self._launched_urls: list[str] = []

    def launch(self, url: str) -> None:
        """Capture URL without opening browser.

        Args:
            url: The URL that would have been opened
        """
        self._launched_urls.append(url)

    @property
    def launched_urls(self) -> list[str]:
        """Get the list of URLs that were launched.

        Returns list of URL strings passed to launch().

        This property is for test assertions only.
        """
        return self._launched_urls
