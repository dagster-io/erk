"""Fake UserFeedback for testing."""

import click

from erk_shared.integrations.feedback.abc import UserFeedback
from erk_shared.output.output import user_output


class FakeUserFeedback(UserFeedback):
    """Fake that captures messages for testing assertions.

    Also outputs messages via user_output() so CliRunner can capture them
    in result.output. This allows tests to check both:
    - Captured messages (via fake_feedback.messages)
    - CLI output (via result.output from CliRunner)

    Usage in tests:
        fake_feedback = FakeUserFeedback()
        ctx = ErkContext.for_test(feedback=fake_feedback)

        # Run command
        result = runner.invoke(command, obj=ctx)

        # Assert on captured messages
        assert "Fetching issue from GitHub..." in fake_feedback.messages
        assert "INFO: Issue: My Feature" in fake_feedback.messages

        # Or assert on CLI output
        assert "Error: Something went wrong" in result.output
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

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

    def clear(self) -> None:
        """Clear captured messages (useful between test steps)."""
        self.messages.clear()

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
