"""Console abstraction combining TTY detection, user feedback, and confirmation prompts.

This module provides a unified Console ABC that replaces the separate Terminal
and UserFeedback abstractions, adding support for confirmation prompts.
"""

from abc import ABC, abstractmethod


class Console(ABC):
    """Abstract console operations for dependency injection.

    Combines:
    - TTY detection (from Terminal)
    - Mode-aware output (from UserFeedback)
    - User prompts (new confirm method)

    Two production implementations:
    - InteractiveConsole: Shows all output, prompts user for confirms
    - ScriptConsole: Suppresses info/success, returns default for confirms
    """

    # TTY detection (from Terminal)

    @abstractmethod
    def is_stdin_interactive(self) -> bool:
        """Check if stdin is connected to an interactive terminal (TTY).

        Returns:
            True if stdin is a TTY, False otherwise
        """
        ...

    @abstractmethod
    def is_stdout_tty(self) -> bool:
        """Check if stdout is connected to a TTY.

        Returns:
            True if stdout is a TTY, False otherwise
        """
        ...

    @abstractmethod
    def is_stderr_tty(self) -> bool:
        """Check if stderr is connected to a TTY.

        Returns:
            True if stderr is a TTY, False otherwise
        """
        ...

    # Output (from UserFeedback)

    @abstractmethod
    def info(self, message: str) -> None:
        """Show informational message (suppressed in script mode)."""
        ...

    @abstractmethod
    def success(self, message: str) -> None:
        """Show success message (suppressed in script mode)."""
        ...

    @abstractmethod
    def error(self, message: str) -> None:
        """Show error message (always shown, even in script mode)."""
        ...

    # User prompts (new)

    @abstractmethod
    def confirm(self, prompt: str, *, default: bool | None) -> bool:
        """Prompt user for confirmation.

        In interactive mode: shows prompt and waits for user input.
        In script mode: returns the default value (raises if default is None).

        Args:
            prompt: The confirmation prompt to display.
            default: Default response when user just presses enter.
                     True for [Y/n], False for [y/N], None to require explicit input.

        Returns:
            True if the user confirmed, False otherwise.

        Raises:
            ValueError: In script mode when default is None (requires explicit choice).
        """
        ...
