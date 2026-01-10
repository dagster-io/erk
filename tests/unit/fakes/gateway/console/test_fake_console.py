"""Unit tests for FakeConsole - Layer 1 (Fake Infrastructure Tests)."""

import pytest

from erk_shared.gateway.console.fake import FakeConsole


class TestFakeConsoleTTYState:
    """Tests for TTY detection state configuration."""

    def test_is_interactive_returns_configured_value(self) -> None:
        """is_stdin_interactive returns the configured is_interactive value."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        assert console.is_stdin_interactive() is True

        console_non_interactive = FakeConsole(
            is_interactive=False,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        assert console_non_interactive.is_stdin_interactive() is False

    def test_stdout_tty_defaults_to_interactive(self) -> None:
        """is_stdout_tty defaults to is_interactive when None."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        assert console.is_stdout_tty() is True

    def test_stdout_tty_uses_explicit_value(self) -> None:
        """is_stdout_tty uses explicit value when provided."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=False,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        assert console.is_stdout_tty() is False

    def test_stderr_tty_defaults_to_interactive(self) -> None:
        """is_stderr_tty defaults to is_interactive when None."""
        console = FakeConsole(
            is_interactive=False,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        assert console.is_stderr_tty() is False

    def test_stderr_tty_uses_explicit_value(self) -> None:
        """is_stderr_tty uses explicit value when provided."""
        console = FakeConsole(
            is_interactive=False,
            is_stdout_tty=None,
            is_stderr_tty=True,
            confirm_responses=None,
        )
        assert console.is_stderr_tty() is True


class TestFakeConsoleMessages:
    """Tests for message capture functionality."""

    def test_info_captures_message_with_prefix(self) -> None:
        """info() captures message with INFO: prefix."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.info("Starting operation...")

        assert "INFO: Starting operation..." in console.messages

    def test_success_captures_message_with_prefix(self) -> None:
        """success() captures message with SUCCESS: prefix."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.success("Operation complete")

        assert "SUCCESS: Operation complete" in console.messages

    def test_error_captures_message_with_prefix(self) -> None:
        """error() captures message with ERROR: prefix."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.error("Something went wrong")

        assert "ERROR: Something went wrong" in console.messages

    def test_multiple_messages_captured_in_order(self) -> None:
        """Multiple messages are captured in call order."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.info("First")
        console.success("Second")
        console.error("Third")

        assert console.messages == [
            "INFO: First",
            "SUCCESS: Second",
            "ERROR: Third",
        ]


class TestFakeConsoleConfirm:
    """Tests for confirm() functionality."""

    def test_confirm_returns_configured_responses_in_order(self) -> None:
        """confirm() returns responses in configured order."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True, False, True],
        )

        assert console.confirm("First?", default=None) is True
        assert console.confirm("Second?", default=None) is False
        assert console.confirm("Third?", default=None) is True

    def test_confirm_captures_prompts(self) -> None:
        """confirm() captures the prompt strings."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )

        console.confirm("Delete file?", default=False)

        assert "Delete file?" in console.confirm_prompts

    def test_confirm_raises_when_no_response_configured(self) -> None:
        """confirm() raises AssertionError when responses exhausted."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[],
        )

        with pytest.raises(AssertionError) as exc_info:
            console.confirm("Proceed?", default=None)

        assert "no response configured" in str(exc_info.value)
        assert "Proceed?" in str(exc_info.value)

    def test_confirm_raises_when_responses_exhausted(self) -> None:
        """confirm() raises AssertionError after consuming all responses."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )

        console.confirm("First?", default=None)

        with pytest.raises(AssertionError):
            console.confirm("Second?", default=None)


class TestFakeConsoleHelpers:
    """Tests for helper methods."""

    def test_clear_resets_messages_and_prompts(self) -> None:
        """clear() resets all captured data."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True, False],
        )
        console.info("Message")
        console.confirm("Prompt?", default=None)

        console.clear()

        assert console.messages == []
        assert console.confirm_prompts == []

    def test_clear_resets_confirm_index(self) -> None:
        """clear() resets confirm index to reuse responses."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        console.confirm("First?", default=None)
        console.clear()

        # Should be able to get the response again
        assert console.confirm("After clear?", default=None) is True

    def test_assert_contains_succeeds_on_match(self) -> None:
        """assert_contains() succeeds when message contains expected text."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.info("Processing file: config.yaml")

        # Should not raise
        console.assert_contains("config.yaml")

    def test_assert_contains_raises_on_no_match(self) -> None:
        """assert_contains() raises AssertionError when no match found."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.info("Something else")

        with pytest.raises(AssertionError) as exc_info:
            console.assert_contains("not found")

        assert "not found" in str(exc_info.value)
        assert "Something else" in str(exc_info.value)

    def test_assert_not_contains_succeeds_on_no_match(self) -> None:
        """assert_not_contains() succeeds when message not present."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.info("Good message")

        # Should not raise
        console.assert_not_contains("bad")

    def test_assert_not_contains_raises_on_match(self) -> None:
        """assert_not_contains() raises AssertionError when match found."""
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        console.error("Unexpected error occurred")

        with pytest.raises(AssertionError) as exc_info:
            console.assert_not_contains("error")

        assert "error" in str(exc_info.value)
