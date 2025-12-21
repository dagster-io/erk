"""Tests for RealGitHubAdmin with mocked subprocess execution.

These tests verify that RealGitHubAdmin correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import subprocess

from pytest import MonkeyPatch

from erk.core.implementation_queue.github.real import RealGitHubAdmin
from tests.integration.test_helpers import mock_subprocess_run

# ============================================================================
# check_auth_status() Tests
# ============================================================================


def test_check_auth_status_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status when user is logged in."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == ["gh", "auth", "status"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="github.com\n  ✓ Logged in to github.com account testuser (keyring)\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "testuser"
        assert result.error is None


def test_check_auth_status_authenticated_with_parens(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status parses username correctly when followed by parens."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=(
                "github.com\n  ✓ Logged in to github.com account schrockn (github.com/schrockn)\n"
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "schrockn"
        assert result.error is None


def test_check_auth_status_not_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status when user is not logged in."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="You are not logged into any GitHub hosts. Run gh auth login to authenticate.",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error is None


def test_check_auth_status_timeout(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status handles timeout gracefully."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd, 10)

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error == "Auth check timed out"


def test_check_auth_status_os_error(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status handles OSError (e.g., gh not installed)."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise OSError("No such file or directory: 'gh'")

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error == "No such file or directory: 'gh'"


def test_check_auth_status_output_in_stderr(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status reads from stderr when stdout is empty."""
    # Some versions of gh output to stderr

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="github.com\n  ✓ Logged in to github.com account anotheruser (keyring)\n",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "anotheruser"
        assert result.error is None
