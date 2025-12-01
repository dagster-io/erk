"""Real implementation of LiveDisplay using Rich Live."""

from rich.console import Console, RenderableType
from rich.live import Live

from erk.core.display.abc import LiveDisplay


class RealLiveDisplay(LiveDisplay):
    """Real implementation using Rich Live."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(stderr=True, width=200, force_terminal=True)
        self._live: Live | None = None

    def start(self) -> None:
        """Start live display mode."""
        self._live = Live(console=self._console, refresh_per_second=4)
        self._live.start()

    def update(self, renderable: RenderableType) -> None:
        """Update the display with new content."""
        if self._live is not None:
            self._live.update(renderable)

    def stop(self) -> None:
        """Stop live display mode."""
        if self._live is not None:
            self._live.stop()
            self._live = None
