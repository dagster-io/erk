"""Real BrowserLauncher implementation using click.launch."""

import click

from erk_shared.integrations.browser.abc import BrowserLauncher


class RealBrowserLauncher(BrowserLauncher):
    """Production implementation that opens URLs in the system browser."""

    def launch(self, url: str) -> None:
        """Launch URL in the default web browser.

        Args:
            url: The URL to open in the browser
        """
        click.launch(url)
