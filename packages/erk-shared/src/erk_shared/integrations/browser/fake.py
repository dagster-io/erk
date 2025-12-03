"""Fake BrowserLauncher implementation for testing.

FakeBrowserLauncher is an in-memory implementation that tracks launch() calls
without actually opening browser windows, enabling fast and deterministic tests.
"""

from erk_shared.integrations.browser.abc import BrowserLauncher


class FakeBrowserLauncher(BrowserLauncher):
    """In-memory fake implementation that tracks launch calls.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(self, should_succeed: bool = True) -> None:
        """Create FakeBrowserLauncher with configurable success behavior.

        Args:
            should_succeed: Whether launch() should return True or False.
                Defaults to True for most tests.
        """
        self._should_succeed = should_succeed
        self._launch_calls: list[str] = []

    @property
    def launch_calls(self) -> list[str]:
        """Get the list of launch() calls that were made.

        Returns a copy of the list to prevent external mutation.

        This property is for test assertions only.
        """
        return list(self._launch_calls)

    @property
    def last_launched(self) -> str | None:
        """Get the last URL that was launched, or None if no launch calls.

        This property is for test assertions only.
        """
        if not self._launch_calls:
            return None
        return self._launch_calls[-1]

    def launch(self, url: str) -> bool:
        """Track launch call and return configured success state.

        Args:
            url: URL that would have been launched in browser

        Returns:
            The configured should_succeed value
        """
        self._launch_calls.append(url)
        return self._should_succeed
