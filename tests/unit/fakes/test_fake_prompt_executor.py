"""Tests for FakePromptExecutor.

Tests that verify the fake implementation correctly simulates
typed events for testing error handling.
"""

from pathlib import Path

from erk.core.prompt_executor import NoOutputEvent, ProcessErrorEvent
from tests.fakes.prompt_executor import FakePromptExecutor


def test_fake_prompt_executor_simulates_no_output() -> None:
    """Test that FakePromptExecutor yields NoOutputEvent when configured."""
    fake = FakePromptExecutor(simulated_no_output=True)

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
            permission_mode="edits",
        )
    )

    assert len(events) == 1
    assert isinstance(events[0], NoOutputEvent)
    assert "no output" in events[0].diagnostic.lower()


def test_fake_prompt_executor_simulates_process_error() -> None:
    """Test that FakePromptExecutor yields ProcessErrorEvent when configured."""
    fake = FakePromptExecutor(
        simulated_process_error="Failed to start Claude CLI: Permission denied"
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
            permission_mode="edits",
        )
    )

    assert len(events) == 1
    assert isinstance(events[0], ProcessErrorEvent)
    assert "Permission denied" in events[0].message


def test_fake_prompt_executor_process_error_takes_precedence() -> None:
    """Test that ProcessErrorEvent takes precedence over NoOutputEvent."""
    fake = FakePromptExecutor(
        simulated_no_output=True,
        simulated_process_error="Process failed",
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
            permission_mode="edits",
        )
    )

    # Process error should take precedence
    assert len(events) == 1
    assert isinstance(events[0], ProcessErrorEvent)


def test_fake_prompt_executor_no_output_takes_precedence_over_command_fail() -> None:
    """Test that NoOutputEvent takes precedence over command_should_fail."""
    fake = FakePromptExecutor(
        simulated_no_output=True,
        command_should_fail=True,
    )

    events = list(
        fake.execute_command_streaming(
            command="/test:command",
            worktree_path=Path("/fake/path"),
            dangerous=False,
            permission_mode="edits",
        )
    )

    # no_output should take precedence over command_should_fail
    assert len(events) == 1
    assert isinstance(events[0], NoOutputEvent)


def test_execute_prompt_passthrough_returns_configured_exit_code() -> None:
    """Test that execute_prompt_passthrough returns the configured exit code."""
    fake = FakePromptExecutor(simulated_passthrough_exit_code=5)

    exit_code = fake.execute_prompt_passthrough(
        "test prompt",
        model="sonnet",
        tools=["Read"],
        cwd=Path("/tmp"),
        dangerous=True,
    )

    assert exit_code == 5


def test_execute_prompt_passthrough_default_exit_code_is_zero() -> None:
    """Test that execute_prompt_passthrough defaults to exit code 0."""
    fake = FakePromptExecutor()

    exit_code = fake.execute_prompt_passthrough(
        "test prompt",
        model="haiku",
        tools=None,
        cwd=Path("/a"),
        dangerous=False,
    )

    assert exit_code == 0


def test_execute_prompt_passthrough_tracks_calls() -> None:
    """Test that execute_prompt_passthrough tracks all call arguments."""
    fake = FakePromptExecutor()

    fake.execute_prompt_passthrough(
        "prompt1",
        model="haiku",
        tools=None,
        cwd=Path("/a"),
        dangerous=False,
    )
    fake.execute_prompt_passthrough(
        "prompt2",
        model="opus",
        tools=["Bash", "Read"],
        cwd=Path("/b"),
        dangerous=True,
    )

    assert len(fake.passthrough_calls) == 2
    assert fake.passthrough_calls[0] == ("prompt1", "haiku", None, Path("/a"), False)
    assert fake.passthrough_calls[1] == ("prompt2", "opus", ["Bash", "Read"], Path("/b"), True)
