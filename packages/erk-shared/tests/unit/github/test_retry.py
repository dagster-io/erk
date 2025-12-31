"""Tests for GitHub retry utility."""

from __future__ import annotations

import pytest

from erk_shared.gateway.time.fake import FakeTime
from erk_shared.github.retry import RETRY_DELAYS, ShouldRetry, with_github_retry


def test_success_on_first_attempt():
    """Test successful operation on first attempt."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 1
    assert fake_time.sleep_calls == []


def test_success_on_second_attempt():
    """Test successful operation after one retry."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ShouldRetry("First attempt failed")
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 2
    assert fake_time.sleep_calls == [RETRY_DELAYS[0]]


def test_success_on_third_attempt():
    """Test successful operation after two retries."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ShouldRetry(f"Attempt {call_count} failed")
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == RETRY_DELAYS


def test_all_attempts_fail():
    """Test when all retry attempts are exhausted."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        raise ShouldRetry(f"Attempt {call_count} failed")

    with pytest.raises(ShouldRetry, match="Attempt 3 failed"):
        with_github_retry(fake_time, "test operation", operation)

    # Should try 3 times total (1 initial + 2 retries)
    assert call_count == 3
    assert fake_time.sleep_calls == RETRY_DELAYS


def test_non_retryable_exception_bubbles():
    """Test that exceptions other than ShouldRetry bubble immediately."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent error")

    with pytest.raises(ValueError, match="Permanent error"):
        with_github_retry(fake_time, "test operation", operation)

    # Should only try once - no retries for permanent errors
    assert call_count == 1
    assert fake_time.sleep_calls == []


def test_custom_retry_delays():
    """Test using custom retry delays for polling."""
    fake_time = FakeTime()
    call_count = 0
    custom_delays = [2.0, 2.0, 2.0]  # Constant 2s interval

    def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ShouldRetry(f"Attempt {call_count} not ready")
        return "success"

    result = with_github_retry(
        fake_time,
        "poll operation",
        operation,
        retry_delays=custom_delays,
    )

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == [2.0, 2.0]


def test_custom_delays_all_fail():
    """Test exhausting custom retry delays."""
    fake_time = FakeTime()
    call_count = 0
    custom_delays = [1.0, 2.0, 4.0]

    def operation():
        nonlocal call_count
        call_count += 1
        raise ShouldRetry(f"Attempt {call_count} failed")

    with pytest.raises(ShouldRetry, match="Attempt 4 failed"):
        with_github_retry(
            fake_time,
            "poll operation",
            operation,
            retry_delays=custom_delays,
        )

    # Should try 4 times total (1 initial + 3 retries from delays)
    assert call_count == 4
    assert fake_time.sleep_calls == custom_delays


def test_empty_retry_delays():
    """Test with empty retry delays (fail immediately)."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        raise ShouldRetry("Failed")

    with pytest.raises(ShouldRetry, match="Failed"):
        with_github_retry(
            fake_time,
            "test operation",
            operation,
            retry_delays=[],
        )

    # Should try only once
    assert call_count == 1
    assert fake_time.sleep_calls == []


def test_return_type_preservation():
    """Test that return type is preserved correctly."""
    fake_time = FakeTime()

    # Test with dict
    def dict_operation():
        return {"key": "value"}

    result = with_github_retry(fake_time, "dict op", dict_operation)
    assert isinstance(result, dict)
    assert result == {"key": "value"}

    # Test with list
    def list_operation():
        return [1, 2, 3]

    result = with_github_retry(fake_time, "list op", list_operation)
    assert isinstance(result, list)
    assert result == [1, 2, 3]

    # Test with int
    def int_operation():
        return 42

    result = with_github_retry(fake_time, "int op", int_operation)
    assert isinstance(result, int)
    assert result == 42


def test_callback_handles_multiple_exception_types():
    """Test callback converting multiple exception types to ShouldRetry."""
    fake_time = FakeTime()
    call_count = 0

    def operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            try:
                raise RuntimeError("Transient error")
            except RuntimeError as e:
                raise ShouldRetry(f"API error: {e}") from e
        if call_count == 2:
            try:
                raise FileNotFoundError("File not found")
            except FileNotFoundError as e:
                raise ShouldRetry(f"API error: {e}") from e
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == RETRY_DELAYS


def test_polling_pattern_eventual_consistency():
    """Test polling pattern for eventual consistency."""
    fake_time = FakeTime()
    call_count = 0
    poll_interval = 2.0
    max_attempts = 5
    custom_delays = [poll_interval] * max_attempts

    def poll_for_resource():
        nonlocal call_count
        call_count += 1
        # Simulate resource appearing after 3 polls
        if call_count < 3:
            raise ShouldRetry("Resource not found yet")
        return {"id": "123", "status": "ready"}

    result = with_github_retry(
        fake_time,
        "poll for resource",
        poll_for_resource,
        retry_delays=custom_delays,
    )

    assert result == {"id": "123", "status": "ready"}
    assert call_count == 3
    assert fake_time.sleep_calls == [2.0, 2.0]


def test_transient_error_pattern():
    """Test transient error retry pattern with exponential backoff."""
    fake_time = FakeTime()
    call_count = 0

    def fetch_with_retry():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            try:
                raise RuntimeError("502 Bad Gateway")
            except RuntimeError as e:
                raise ShouldRetry(f"API error: {e}") from e
        return {"data": "success"}

    result = with_github_retry(fake_time, "fetch comment", fetch_with_retry)

    assert result == {"data": "success"}
    assert call_count == 2
    assert fake_time.sleep_calls == [RETRY_DELAYS[0]]


def test_should_retry_exception_chaining():
    """Test that ShouldRetry properly chains exceptions."""
    fake_time = FakeTime()

    def operation():
        try:
            raise ValueError("Original error")
        except ValueError as e:
            raise ShouldRetry("Retrying") from e

    with pytest.raises(ShouldRetry) as exc_info:
        with_github_retry(
            fake_time,
            "test operation",
            operation,
            retry_delays=[],
        )

    # Check exception chaining
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "Original error"
