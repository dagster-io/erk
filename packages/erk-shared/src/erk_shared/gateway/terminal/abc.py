"""Terminal operations abstraction for testing.

This module provides an ABC for terminal/TTY detection to enable
fast tests that don't rely on actual terminal state.
"""

from abc import ABC, abstractmethod


class Terminal(ABC):
    """Abstract terminal operations for dependency injection."""

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
