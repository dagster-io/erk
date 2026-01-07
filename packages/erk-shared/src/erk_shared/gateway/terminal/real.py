"""Real terminal implementation using sys.stdin.isatty() and os.isatty()."""

import os
import sys

from erk_shared.gateway.terminal.abc import Terminal


class RealTerminal(Terminal):
    """Production implementation using sys.stdin.isatty() and os.isatty()."""

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
