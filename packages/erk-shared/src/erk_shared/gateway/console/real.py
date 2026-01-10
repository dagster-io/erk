"""Real Console implementations for production use."""

import os
import sys

import click

from erk_shared.gateway.console.abc import Console
from erk_shared.output.output import user_output


class InteractiveConsole(Console):
    """Console for interactive mode - shows all output and prompts user.

    Used when running commands directly from a terminal without --script flag.
    """

    def is_stdin_interactive(self) -> bool:
        """Check if stdin is connected to an interactive terminal.

        Returns:
            True if stdin is a TTY, False otherwise
        """
        return sys.stdin.isatty()

    def is_stdout_tty(self) -> bool:
        """Check if stdout is connected to a TTY.

        Returns:
            True if stdout is a TTY, False otherwise
        """
        return os.isatty(1)

    def is_stderr_tty(self) -> bool:
        """Check if stderr is connected to a TTY.

        Returns:
            True if stderr is a TTY, False otherwise
        """
        return os.isatty(2)

    def info(self, message: str) -> None:
        """Show informational message."""
        user_output(message)

    def success(self, message: str) -> None:
        """Show success message in green."""
        user_output(click.style(message, fg="green"))

    def error(self, message: str) -> None:
        """Show error message in red."""
        user_output(click.style(message, fg="red"))

    def confirm(self, prompt: str, *, default: bool | None) -> bool:
        """Prompt user for confirmation with proper stderr flushing.

        Args:
            prompt: The confirmation prompt to display.
            default: Default response when user just presses enter.
                     True for [Y/n], False for [y/N], None to require explicit input.

        Returns:
            True if the user confirmed, False otherwise.
        """
        sys.stderr.flush()
        return click.confirm(prompt, default=default, err=True)


class ScriptConsole(Console):
    """Console for script mode - suppresses output and auto-confirms.

    Used when --script flag is active to keep output clean for
    shell integration handler to parse activation script path.
    """

    def is_stdin_interactive(self) -> bool:
        """Check if stdin is connected to an interactive terminal.

        Returns:
            True if stdin is a TTY, False otherwise
        """
        return sys.stdin.isatty()

    def is_stdout_tty(self) -> bool:
        """Check if stdout is connected to a TTY.

        Returns:
            True if stdout is a TTY, False otherwise
        """
        return os.isatty(1)

    def is_stderr_tty(self) -> bool:
        """Check if stderr is connected to a TTY.

        Returns:
            True if stderr is a TTY, False otherwise
        """
        return os.isatty(2)

    def info(self, message: str) -> None:
        """Suppress informational message in script mode."""

    def success(self, message: str) -> None:
        """Suppress success message in script mode."""

    def error(self, message: str) -> None:
        """Show error message even in script mode."""
        user_output(click.style(message, fg="red"))

    def confirm(self, prompt: str, *, default: bool | None) -> bool:
        """Return default value without prompting.

        In script mode, we can't interactively prompt the user.
        If a default is provided, use it. If not, raise an error.

        Args:
            prompt: The confirmation prompt (ignored in script mode).
            default: Default response to return automatically.

        Returns:
            The default value.

        Raises:
            ValueError: When default is None (script mode requires explicit default).
        """
        if default is None:
            raise ValueError(f"Script mode requires a default value for confirmation: {prompt}")
        return default
