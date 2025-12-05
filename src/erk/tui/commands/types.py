"""Data types for command palette."""

from collections.abc import Callable
from dataclasses import dataclass

from erk.tui.data.types import PlanRowData


@dataclass(frozen=True)
class CommandContext:
    """Context available to commands.

    Attributes:
        row: The plan row data for the selected plan
    """

    row: PlanRowData


@dataclass(frozen=True)
class CommandDefinition:
    """Definition of a command in the command palette.

    Attributes:
        id: Unique identifier for the command (e.g., "close_plan")
        name: Display name (e.g., "Close Plan")
        description: Brief description of what the command does
        shortcut: Optional keyboard shortcut for display (e.g., "c")
        is_available: Predicate function to check if command is available
    """

    id: str
    name: str
    description: str
    shortcut: str | None
    is_available: Callable[[CommandContext], bool]
