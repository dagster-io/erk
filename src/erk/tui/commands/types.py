"""Data types for command palette."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from erk.tui.data.types import PrRowData, RunRowData
from erk.tui.views.types import ViewMode


class CommandCategory(Enum):
    """Category of a command in the command palette.

    Used to determine the emoji prefix displayed in the palette.
    """

    ACTION = auto()  # ⚡ Mutative operations
    OPEN = auto()  # 🔗 Browser navigation
    COPY = auto()  # 📋 Clipboard operations


@dataclass(frozen=True)
class CommandContext:
    """Context available to commands.

    Attributes:
        row: The plan row data for the selected plan
        view_mode: The active view mode (plans, learn, objectives)
    """

    row: PrRowData
    view_mode: ViewMode
    cmux_integration: bool = False


@dataclass(frozen=True)
class RunCommandContext:
    """Context available to run commands.

    Attributes:
        row: The run row data for the selected workflow run
        view_mode: The active view mode (always RUNS)
    """

    row: RunRowData
    view_mode: ViewMode


@dataclass(frozen=True)
class CommandDefinition:
    """Definition of a command in the command palette.

    Attributes:
        id: Unique identifier for the command (e.g., "close_pr")
        name: Display name (e.g., "Close Plan")
        description: Brief description of what the command does
        category: Command category for emoji prefix display
        shortcut: Optional keyboard shortcut for display (e.g., "c")
        launch_key: Optional single-key binding for the Launch modal (e.g., "c").
            Only ACTION commands should have a launch_key.
        is_available: Predicate function to check if command is available
        get_display_name: Optional function to generate context-aware display name.
            If provided, returns the name to show in the palette
            (e.g., "erk slot co --for-plan 123").
            If None, falls back to the static `name` field.
    """

    id: str
    name: str
    description: str
    category: CommandCategory
    shortcut: str | None
    launch_key: str | None
    is_available: Callable[[CommandContext], bool]
    get_display_name: Callable[[CommandContext], str] | None
