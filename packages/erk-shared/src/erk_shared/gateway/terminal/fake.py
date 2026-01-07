"""Fake Terminal implementation for testing.

FakeTerminal is an in-memory implementation that returns a configurable
interactive state, enabling fast and deterministic tests.
"""

from erk_shared.gateway.terminal.abc import Terminal


class FakeTerminal(Terminal):
    """In-memory fake implementation that returns configured state.

    This class has NO public setup methods. All state is provided via constructor.
    """

    def __init__(
        self,
        *,
        is_interactive: bool,
        is_stdout_tty: bool | None,
        is_stderr_tty: bool | None,
    ) -> None:
        """Create FakeTerminal with configured TTY state.

        Args:
            is_interactive: Whether to report stdin as interactive (TTY)
            is_stdout_tty: Whether to report stdout as a TTY.
                If None, defaults to is_interactive.
            is_stderr_tty: Whether to report stderr as a TTY.
                If None, defaults to is_interactive.
        """
        self._is_interactive = is_interactive
        # Default stdout/stderr to match stdin if not explicitly specified
        self._is_stdout_tty = is_stdout_tty if is_stdout_tty is not None else is_interactive
        self._is_stderr_tty = is_stderr_tty if is_stderr_tty is not None else is_interactive

    def is_stdin_interactive(self) -> bool:
        """Return the configured interactive state.

        Returns:
            The is_interactive value configured at construction time.
        """
        return self._is_interactive

    def is_stdout_tty(self) -> bool:
        """Return the configured stdout TTY state.

        Returns:
            The is_stdout_tty value (or is_interactive if not specified).
        """
        return self._is_stdout_tty

    def is_stderr_tty(self) -> bool:
        """Return the configured stderr TTY state.

        Returns:
            The is_stderr_tty value (or is_interactive if not specified).
        """
        return self._is_stderr_tty
