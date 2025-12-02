"""TUI runner abstraction for testability.

This module provides an ABC for running Textual TUI applications, enabling
CLI routing tests without starting the Textual event loop (which would
leave threads running and cause pytest-xdist workers to hang).
"""

from abc import ABC, abstractmethod

from erk.tui.app import ErkDashApp


class TuiRunner(ABC):
    """Abstract interface for running TUI applications."""

    @abstractmethod
    def run(self, app: ErkDashApp) -> None:
        """Run the TUI application.

        Args:
            app: The ErkDashApp instance to run
        """
        ...


class RealTuiRunner(TuiRunner):
    """Production implementation that runs the Textual event loop."""

    def run(self, app: ErkDashApp) -> None:
        """Run the app's Textual event loop.

        Args:
            app: The ErkDashApp instance to run
        """
        app.run()


class FakeTuiRunner(TuiRunner):
    """Test implementation that captures apps without running the event loop.

    This class captures app instances passed to run() without actually
    starting the Textual event loop, enabling CLI routing tests to verify
    that the correct app was created with correct parameters.
    """

    def __init__(self) -> None:
        """Create FakeTuiRunner with empty app tracking."""
        self._apps_run: list[ErkDashApp] = []

    def run(self, app: ErkDashApp) -> None:
        """Capture app without running event loop.

        Args:
            app: The ErkDashApp that would have been run
        """
        self._apps_run.append(app)

    @property
    def apps_run(self) -> list[ErkDashApp]:
        """Get the list of apps that were passed to run().

        Returns list of ErkDashApp instances that would have been run.

        This property is for test assertions only.
        """
        return self._apps_run
