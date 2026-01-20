"""Tests for FakeReviewExecutor."""

from pathlib import Path

from erk_shared.review_executor.fake import FakeReviewExecutor


def test_fake_executor_returns_configured_exit_code() -> None:
    """FakeReviewExecutor returns the configured exit code."""
    executor = FakeReviewExecutor(exit_code=42)

    result = executor.execute_review(
        prompt="Review this",
        model="claude-sonnet-4-5",
        tools=["Read"],
        cwd=Path("/fake/repo"),
    )

    assert result == 42


def test_fake_executor_records_calls() -> None:
    """FakeReviewExecutor records all review calls."""
    executor = FakeReviewExecutor()

    executor.execute_review(
        prompt="First review",
        model="claude-sonnet-4-5",
        tools=["Read", "Bash"],
        cwd=Path("/repo/one"),
    )
    executor.execute_review(
        prompt="Second review",
        model="gpt-5-codex",
        tools=None,
        cwd=Path("/repo/two"),
    )

    assert len(executor.review_calls) == 2
    assert executor.review_calls[0].prompt == "First review"
    assert executor.review_calls[0].model == "claude-sonnet-4-5"
    assert executor.review_calls[0].tools == ("Read", "Bash")
    assert executor.review_calls[0].cwd == Path("/repo/one")
    assert executor.review_calls[1].prompt == "Second review"
    assert executor.review_calls[1].model == "gpt-5-codex"
    assert executor.review_calls[1].tools is None
    assert executor.review_calls[1].cwd == Path("/repo/two")


def test_fake_executor_is_available_by_default() -> None:
    """FakeReviewExecutor.is_available() returns True by default."""
    executor = FakeReviewExecutor()

    assert executor.is_available() is True


def test_fake_executor_is_available_configurable() -> None:
    """FakeReviewExecutor.is_available() returns configured value."""
    executor = FakeReviewExecutor(is_available=False)

    assert executor.is_available() is False


def test_fake_executor_default_exit_code_is_zero() -> None:
    """FakeReviewExecutor returns exit code 0 by default."""
    executor = FakeReviewExecutor()

    result = executor.execute_review(
        prompt="Review",
        model="model",
        tools=None,
        cwd=Path("/repo"),
    )

    assert result == 0
