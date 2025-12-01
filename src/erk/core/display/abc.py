"""Abstract interface for live-updating terminal display."""

from abc import ABC, abstractmethod

from rich.console import RenderableType


class LiveDisplay(ABC):
    """Abstract interface for live-updating terminal display."""

    @abstractmethod
    def start(self) -> None:
        """Start live display mode."""
        ...

    @abstractmethod
    def update(self, renderable: RenderableType) -> None:
        """Update the display with new content."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop live display mode."""
        ...
