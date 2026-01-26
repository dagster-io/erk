"""Tests for execute_gh_command_with_retry in parsing module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from erk_shared.gateway.github.parsing import execute_gh_command_with_retry
from erk_shared.gateway.github.retry import RETRY_DELAYS
from erk_shared.gateway.time.fake import FakeTime


def test_success_on_first_attempt() -> None:
    """Test successful command on first attempt."""
    fake_time = FakeTime()
    cwd = Path("/repo")

    with patch("erk_shared.gateway.github.parsing.execute_gh_command") as mock_cmd:
        mock_cmd.return_value = '{"data": "test"}'
        result = execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    assert result == '{"data": "test"}'
    assert mock_cmd.call_count == 1
    assert fake_time.sleep_calls == []


def test_retry_on_io_timeout() -> None:
    """Test retry when i/o timeout occurs."""
    fake_time = FakeTime()
    cwd = Path("/repo")
    call_count = 0

    def mock_execute(cmd: list[str], path: Path) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("dial tcp 140.82.116.5:443: i/o timeout")
        return "success"

    with patch("erk_shared.gateway.github.parsing.execute_gh_command", side_effect=mock_execute):
        result = execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    assert result == "success"
    assert call_count == 2
    assert fake_time.sleep_calls == [RETRY_DELAYS[0]]


def test_retry_on_connection_refused() -> None:
    """Test retry when connection refused occurs."""
    fake_time = FakeTime()
    cwd = Path("/repo")
    call_count = 0

    def mock_execute(cmd: list[str], path: Path) -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("connect: connection refused")
        return "success"

    with patch("erk_shared.gateway.github.parsing.execute_gh_command", side_effect=mock_execute):
        result = execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == list(RETRY_DELAYS)


def test_raises_runtime_error_after_retries_exhausted() -> None:
    """Test that RuntimeError is raised after all retries exhausted."""
    fake_time = FakeTime()
    cwd = Path("/repo")

    with patch("erk_shared.gateway.github.parsing.execute_gh_command") as mock_cmd:
        mock_cmd.side_effect = RuntimeError("dial tcp: i/o timeout")

        with pytest.raises(RuntimeError, match="GitHub command failed after retries"):
            execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    # Should try 3 times (1 initial + 2 retries)
    assert mock_cmd.call_count == 3
    assert fake_time.sleep_calls == list(RETRY_DELAYS)


def test_non_transient_error_raises_immediately() -> None:
    """Test that non-transient errors raise immediately without retry."""
    fake_time = FakeTime()
    cwd = Path("/repo")

    with patch("erk_shared.gateway.github.parsing.execute_gh_command") as mock_cmd:
        mock_cmd.side_effect = RuntimeError("HTTP 404: Not Found")

        with pytest.raises(RuntimeError, match="HTTP 404: Not Found"):
            execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    # Should only try once - non-transient error
    assert mock_cmd.call_count == 1
    assert fake_time.sleep_calls == []


def test_file_not_found_error_raises_immediately() -> None:
    """Test that FileNotFoundError (gh not installed) raises immediately."""
    fake_time = FakeTime()
    cwd = Path("/repo")

    with patch("erk_shared.gateway.github.parsing.execute_gh_command") as mock_cmd:
        mock_cmd.side_effect = FileNotFoundError("gh: command not found")

        with pytest.raises(FileNotFoundError, match="gh: command not found"):
            execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    # Should only try once - FileNotFoundError is permanent
    assert mock_cmd.call_count == 1
    assert fake_time.sleep_calls == []


def test_custom_retry_delays() -> None:
    """Test using custom retry delays."""
    fake_time = FakeTime()
    cwd = Path("/repo")
    custom_delays = [1.0, 2.0, 4.0]
    call_count = 0

    def mock_execute(cmd: list[str], path: Path) -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("dial tcp: i/o timeout")
        return "success"

    with patch("erk_shared.gateway.github.parsing.execute_gh_command", side_effect=mock_execute):
        result = execute_gh_command_with_retry(
            ["gh", "api", "user"], cwd, fake_time, retry_delays=custom_delays
        )

    assert result == "success"
    assert call_count == 3
    assert fake_time.sleep_calls == [1.0, 2.0]


def test_network_unreachable_is_transient() -> None:
    """Test that network unreachable error triggers retry."""
    fake_time = FakeTime()
    cwd = Path("/repo")
    call_count = 0

    def mock_execute(cmd: list[str], path: Path) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("connect: network is unreachable")
        return "success"

    with patch("erk_shared.gateway.github.parsing.execute_gh_command", side_effect=mock_execute):
        result = execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    assert result == "success"
    assert call_count == 2


def test_rate_limit_error_not_retried() -> None:
    """Test that rate limit errors are not retried (non-transient)."""
    fake_time = FakeTime()
    cwd = Path("/repo")

    with patch("erk_shared.gateway.github.parsing.execute_gh_command") as mock_cmd:
        mock_cmd.side_effect = RuntimeError("HTTP 403: rate limit exceeded")

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            execute_gh_command_with_retry(["gh", "api", "user"], cwd, fake_time)

    assert mock_cmd.call_count == 1
    assert fake_time.sleep_calls == []
