"""Real terminal implementation using sys.stdin.isatty()."""

import sys

from erk_shared.gateway.terminal.abc import Terminal


class RealTerminal(Terminal):
    """Production implementation using sys.stdin.isatty()."""

    def is_stdin_interactive(self) -> bool:
        """Check if stdin is connected to an interactive terminal.

        Returns:
            True if stdin is a TTY, False otherwise
        """
        return sys.stdin.isatty()
