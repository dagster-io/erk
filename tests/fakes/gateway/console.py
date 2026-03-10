"""Fake Console implementation for testing.

FakeConsole is an in-memory implementation that captures messages and
returns configurable responses, enabling fast and deterministic tests.
"""

import click

from erk_shared.gateway.console.abc import Console
from erk_shared.output.output import user_output


class FakeConsole(Console):
    """In-memory fake implementation for testing.

    Captures messages and confirm prompts for test assertions.
    Also outputs messages via user_output() so CliRunner can capture them.

    Usage in tests:
        fake_console = FakeConsole(confirm_responses=[False, True])
        ctx = context_for_test(console=fake_console, ...)

        # Run command
        result = runner.invoke(command, obj=ctx)

        # Assert on captured messages
        assert "INFO: Starting..." in fake_console.messages

        # Assert on confirm prompts shown
        assert "Close issue #42 now?" in fake_console.confirm_prompts
    """

    def __init__(
        self,
        *,
        is_interactive: bool,
        is_stdout_tty: bool | None,
        is_stderr_tty: bool | None,
        confirm_responses: list[bool] | None,
    ) -> None:
        """Create FakeConsole with configured state.

        Args:
            is_interactive: Whether to report stdin as interactive (TTY)
            is_stdout_tty: Whether to report stdout as a TTY.
                If None, defaults to is_interactive.
            is_stderr_tty: Whether to report stderr as a TTY.
                If None, defaults to is_interactive.
            confirm_responses: List of responses to return for confirm() calls.
                Each confirm() call consumes the next response in order.
                If None or empty when confirm() is called, raises an error.
        """
        self._is_interactive = is_interactive
        self._is_stdout_tty = is_stdout_tty if is_stdout_tty is not None else is_interactive
        self._is_stderr_tty = is_stderr_tty if is_stderr_tty is not None else is_interactive
        self._confirm_responses = list(confirm_responses) if confirm_responses else []
        self._confirm_index = 0

        # Captured data for test assertions
        self.messages: list[str] = []
        self.confirm_prompts: list[str] = []

    def is_stdin_interactive(self) -> bool:
        """Return the configured interactive state."""
        return self._is_interactive

    def is_stdout_tty(self) -> bool:
        """Return the configured stdout TTY state."""
        return self._is_stdout_tty

    def is_stderr_tty(self) -> bool:
        """Return the configured stderr TTY state."""
        return self._is_stderr_tty

    def info(self, message: str) -> None:
        """Capture and output info message."""
        self.messages.append(f"INFO: {message}")
        user_output(message)

    def success(self, message: str) -> None:
        """Capture and output success message."""
        self.messages.append(f"SUCCESS: {message}")
        user_output(click.style(message, fg="green"))

    def error(self, message: str) -> None:
        """Capture and output error message."""
        self.messages.append(f"ERROR: {message}")
        user_output(click.style(message, fg="red"))

    def confirm(self, prompt: str, *, default: bool | None) -> bool:
        """Return the next configured response.

        Args:
            prompt: The confirmation prompt (captured for assertions).
            default: Default value (ignored - uses configured responses).

        Returns:
            The next response from confirm_responses list.

        Raises:
            AssertionError: If no more responses are available.
        """
        self.confirm_prompts.append(prompt)

        if self._confirm_index >= len(self._confirm_responses):
            raise AssertionError(
                f"FakeConsole.confirm() called but no response configured.\n"
                f"Prompt: {prompt}\n"
                f"Configure confirm_responses=[...] in FakeConsole constructor."
            )

        response = self._confirm_responses[self._confirm_index]
        self._confirm_index += 1
        return response

    def clear(self) -> None:
        """Clear captured messages and reset confirm index."""
        self.messages.clear()
        self.confirm_prompts.clear()
        self._confirm_index = 0

    def assert_contains(self, expected: str) -> None:
        """Assert that expected message was captured."""
        matches = [msg for msg in self.messages if expected in msg]
        if not matches:
            raise AssertionError(
                f"Expected message containing '{expected}' not found.\n"
                f"Captured messages:\n" + "\n".join(f"  - {msg}" for msg in self.messages)
            )

    def assert_not_contains(self, unexpected: str) -> None:
        """Assert that unexpected message was NOT captured."""
        matches = [msg for msg in self.messages if unexpected in msg]
        if matches:
            raise AssertionError(
                f"Unexpected message containing '{unexpected}' was found:\n"
                + "\n".join(f"  - {msg}" for msg in matches)
            )
