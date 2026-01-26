"""Tests for transient error detection."""

import pytest

from erk_shared.gateway.github.transient_errors import TRANSIENT_ERROR_PATTERNS, is_transient_error


def test_io_timeout_detected() -> None:
    """Test that i/o timeout is detected as transient."""
    error = "dial tcp 140.82.116.5:443: i/o timeout"
    assert is_transient_error(error) is True


def test_dial_tcp_detected() -> None:
    """Test that dial tcp errors are detected as transient."""
    error = "dial tcp: lookup api.github.com: no such host"
    assert is_transient_error(error) is True


def test_connection_refused_detected() -> None:
    """Test that connection refused is detected as transient."""
    error = "connect: connection refused"
    assert is_transient_error(error) is True


def test_could_not_connect_detected() -> None:
    """Test that 'could not connect' is detected as transient."""
    error = "could not connect to server"
    assert is_transient_error(error) is True


def test_network_unreachable_detected() -> None:
    """Test that network unreachable is detected as transient."""
    error = "connect: network is unreachable"
    assert is_transient_error(error) is True


def test_connection_reset_detected() -> None:
    """Test that connection reset is detected as transient."""
    error = "read: connection reset by peer"
    assert is_transient_error(error) is True


def test_connection_timed_out_detected() -> None:
    """Test that connection timed out is detected as transient."""
    error = "connect: connection timed out"
    assert is_transient_error(error) is True


def test_case_insensitive() -> None:
    """Test that detection is case-insensitive."""
    error = "DIAL TCP 140.82.116.5:443: I/O TIMEOUT"
    assert is_transient_error(error) is True


def test_404_not_transient() -> None:
    """Test that 404 errors are not detected as transient."""
    error = "HTTP 404: Not Found"
    assert is_transient_error(error) is False


def test_401_not_transient() -> None:
    """Test that authentication errors are not detected as transient."""
    error = "HTTP 401: Unauthorized - Bad credentials"
    assert is_transient_error(error) is False


def test_rate_limit_not_transient() -> None:
    """Test that rate limit errors are not detected as transient."""
    error = "HTTP 403: rate limit exceeded"
    assert is_transient_error(error) is False


def test_validation_error_not_transient() -> None:
    """Test that validation errors are not detected as transient."""
    error = "HTTP 422: Unprocessable Entity - Validation Failed"
    assert is_transient_error(error) is False


def test_gh_cli_error_not_transient() -> None:
    """Test that gh CLI errors are not detected as transient."""
    error = "gh: could not find issue with number 12345"
    assert is_transient_error(error) is False


def test_empty_string() -> None:
    """Test that empty string is not transient."""
    assert is_transient_error("") is False


def test_patterns_tuple_is_immutable() -> None:
    """Test that TRANSIENT_ERROR_PATTERNS is a tuple (immutable)."""
    assert isinstance(TRANSIENT_ERROR_PATTERNS, tuple)


@pytest.mark.parametrize(
    "pattern",
    TRANSIENT_ERROR_PATTERNS,
)
def test_all_patterns_in_lowercase(pattern: str) -> None:
    """Test that all patterns are lowercase for case-insensitive matching."""
    assert pattern == pattern.lower()
