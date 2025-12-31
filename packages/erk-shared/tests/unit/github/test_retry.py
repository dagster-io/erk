"""Unit tests for GitHub API retry utility."""

from erk_shared.gateway.time.fake import FakeTime
from erk_shared.github.retry import RETRY_DELAYS, with_github_retry


def test_with_github_retry_success_on_first_attempt() -> None:
    """Successful call on first attempt should not retry."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 1
    assert fake_time.sleep_calls == []  # No retries, no sleeps


def test_with_github_retry_success_on_second_attempt() -> None:
    """Failure then success should retry once with correct delay."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient error")
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 2
    assert fake_time.sleep_calls == [RETRY_DELAYS[0]]  # One retry: 0.5s


def test_with_github_retry_success_on_third_attempt() -> None:
    """Two failures then success should retry twice with correct delays."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Transient error")
        return "success"

    result = with_github_retry(fake_time, "test operation", operation)

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == RETRY_DELAYS  # Two retries: [0.5, 1.0]


def test_with_github_retry_all_attempts_fail() -> None:
    """All attempts failing should raise the last exception."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError(f"Persistent error (attempt {call_count})")

    try:
        with_github_retry(fake_time, "test operation", operation)
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError as e:
        assert "Persistent error (attempt 3)" in str(e)

    assert call_count == 3  # 3 total attempts (initial + 2 retries)
    assert fake_time.sleep_calls == RETRY_DELAYS  # Two retries: [0.5, 1.0]


def test_with_github_retry_non_runtime_error_not_retried() -> None:
    """Non-RuntimeError exceptions should not be retried."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Different error type")

    try:
        with_github_retry(fake_time, "test operation", operation)
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Different error type" in str(e)

    assert call_count == 1  # No retries for non-RuntimeError
    assert fake_time.sleep_calls == []


def test_with_github_retry_preserves_return_type() -> None:
    """Verify generic return type works with different types."""
    fake_time = FakeTime()

    # Test with string
    result_str = with_github_retry(fake_time, "str test", lambda: "text")
    assert isinstance(result_str, str)
    assert result_str == "text"

    # Test with int
    result_int = with_github_retry(fake_time, "int test", lambda: 42)
    assert isinstance(result_int, int)
    assert result_int == 42

    # Test with dict
    result_dict = with_github_retry(fake_time, "dict test", lambda: {"key": "value"})
    assert isinstance(result_dict, dict)
    assert result_dict == {"key": "value"}


def test_with_github_retry_uses_operation_name_in_logging(capsys) -> None:
    """Verify operation name appears in error logging (captured to stderr)."""
    fake_time = FakeTime()
    call_count = 0

    def operation() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("First attempt failed")
        return "success"

    with_github_retry(fake_time, "fetch important data", operation)

    # Check stderr output contains operation name
    captured = capsys.readouterr()
    assert "fetch important data" in captured.err
    assert "Successfully completed" in captured.err
