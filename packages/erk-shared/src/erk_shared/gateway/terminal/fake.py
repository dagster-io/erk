"""Fake Terminal implementation for testing.

FakeTerminal is an in-memory implementation that returns a configurable
interactive state, enabling fast and deterministic tests.
"""

from erk_shared.gateway.terminal.abc import Terminal


class FakeTerminal(Terminal):
    """In-memory fake implementation that returns configured state.

    This class has NO public setup methods. All state is provided via constructor.
    """

    def __init__(self, *, is_interactive: bool) -> None:
        """Create FakeTerminal with configured interactive state.

        Args:
            is_interactive: Whether to report stdin as interactive (TTY)
        """
        self._is_interactive = is_interactive

    def is_stdin_interactive(self) -> bool:
        """Return the configured interactive state.

        Returns:
            The is_interactive value configured at construction time.
        """
        return self._is_interactive
