"""Tests for FakeClaudeExecutor.

Tests that verify the fake implementation correctly simulates
no_output and process_error events for testing error handling.
"""

from pathlib import Path

from tests.fakes.claude_executor import FakeClaudeExecutor


def test_fake_claude_executor_simulates_no_output() -> None:
    """Test that FakeClaudeExecutor yields no_output event when configured."""
    fake = FakeClaudeExecutor(simulated_no_output=True)

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
        )
    )

    assert len(events) == 1
    assert events[0].event_type == "no_output"
    assert "no output" in events[0].content.lower()


def test_fake_claude_executor_simulates_process_error() -> None:
    """Test that FakeClaudeExecutor yields process_error event when configured."""
    fake = FakeClaudeExecutor(
        simulated_process_error="Failed to start Claude CLI: Permission denied"
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
        )
    )

    assert len(events) == 1
    assert events[0].event_type == "process_error"
    assert "Permission denied" in events[0].content


def test_fake_claude_executor_process_error_takes_precedence() -> None:
    """Test that process_error takes precedence over no_output."""
    fake = FakeClaudeExecutor(
        simulated_no_output=True,
        simulated_process_error="Process failed",
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
        )
    )

    # Process error should take precedence
    assert len(events) == 1
    assert events[0].event_type == "process_error"


def test_fake_claude_executor_no_output_takes_precedence_over_command_fail() -> None:
    """Test that no_output takes precedence over command_should_fail."""
    fake = FakeClaudeExecutor(
        simulated_no_output=True,
        command_should_fail=True,
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
        )
    )

    # no_output should take precedence over command_should_fail
    assert len(events) == 1
    assert events[0].event_type == "no_output"
