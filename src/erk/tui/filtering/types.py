"""Filter state types for TUI dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FilterMode(Enum):
    """Filter mode state."""

    INACTIVE = auto()
    ACTIVE = auto()


@dataclass(frozen=True)
class FilterState:
    """State for filter mode with progressive escape behavior.

    Attributes:
        mode: Current filter mode (INACTIVE or ACTIVE)
        query: Current filter query text
    """

    mode: FilterMode
    query: str = ""

    @staticmethod
    def initial() -> FilterState:
        """Create initial inactive state."""
        return FilterState(mode=FilterMode.INACTIVE, query="")

    def activate(self) -> FilterState:
        """Activate filter mode."""
        return FilterState(mode=FilterMode.ACTIVE, query=self.query)

    def with_query(self, query: str) -> FilterState:
        """Update query text."""
        return FilterState(mode=self.mode, query=query)

    def handle_escape(self) -> FilterState:
        """Handle escape key with progressive behavior.

        Progressive escape:
        - If text exists, clear it first (stay in active mode)
        - If text is empty, deactivate filter mode

        Returns:
            New state after escape handling
        """
        if self.query:
            # Clear text first, stay in active mode
            return FilterState(mode=FilterMode.ACTIVE, query="")
        # Text already empty, deactivate
        return FilterState(mode=FilterMode.INACTIVE, query="")
