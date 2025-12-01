"""Fake implementation of LiveDisplay for testing.

This fake enables testing live display behavior without
requiring actual terminal output or Rich Live functionality.
"""

from rich.console import RenderableType

from erk.core.display.abc import LiveDisplay


class FakeLiveDisplay(LiveDisplay):
    """In-memory fake for testing live display behavior.

    Constructor Injection:
    - No external state required (starts empty)
    - Tracks all updates for assertions

    When to Use:
    - Testing watch mode loops
    - Verifying display updates are made
    - Testing start/stop lifecycle

    Examples:
        # Test that updates are recorded
        >>> display = FakeLiveDisplay()
        >>> display.start()
        >>> display.update("content")
        >>> assert display.updates == ["content"]

        # Test lifecycle
        >>> display = FakeLiveDisplay()
        >>> display.start()
        >>> assert display.is_active
        >>> display.stop()
        >>> assert not display.is_active
    """

    def __init__(self) -> None:
        """Initialize fake with empty tracking state."""
        self._updates: list[RenderableType] = []
        self._started: bool = False
        self._stopped: bool = False

    @property
    def updates(self) -> list[RenderableType]:
        """Get the list of renderables passed to update().

        This property is for test assertions only.
        """
        return self._updates

    @property
    def is_active(self) -> bool:
        """Whether live display is currently active.

        Returns True if start() was called and stop() was not called.
        """
        return self._started and not self._stopped

    def start(self) -> None:
        """Track that live display was started."""
        self._started = True

    def update(self, renderable: RenderableType) -> None:
        """Track the renderable passed to update."""
        self._updates.append(renderable)

    def stop(self) -> None:
        """Track that live display was stopped."""
        self._stopped = True
