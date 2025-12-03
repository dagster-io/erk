"""Real BrowserLauncher implementation using click.launch().

RealBrowserLauncher provides cross-platform browser launching using click,
which handles xdg-open on Linux, open on macOS, etc.
"""

import click

from erk_shared.integrations.browser.abc import BrowserLauncher


class RealBrowserLauncher(BrowserLauncher):
    """Production implementation using click.launch for browser access."""

    def launch(self, url: str) -> bool:
        """Launch URL in browser using click.launch.

        Args:
            url: URL to open in browser

        Returns:
            True if launch succeeded (click.launch always succeeds)
        """
        click.launch(url)
        return True
