"""Unit tests for RealGitRemoteOps with mocked subprocess calls.

These tests verify command construction and output parsing for
get_remote_ref() and get_local_tracking_ref_sha() without executing git.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_shared.gateway.git.real import RealGit


def test_get_remote_ref_returns_sha() -> None:
    """get_remote_ref returns SHA from git ls-remote output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="abc123def456\trefs/heads/main\n",
            returncode=0,
        )

        ops = RealGit()
        result = ops.remote.get_remote_ref(Path("/test/repo"), "origin", "main")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "ls-remote", "origin", "main"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is False
        assert result == "abc123def456"


def test_get_remote_ref_returns_none_on_error() -> None:
    """get_remote_ref returns None when git ls-remote fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=1)

        ops = RealGit()
        result = ops.remote.get_remote_ref(Path("/test/repo"), "origin", "nonexistent")

        assert result is None


def test_get_remote_ref_returns_none_on_empty_output() -> None:
    """get_remote_ref returns None when ls-remote returns empty output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        ops = RealGit()
        result = ops.remote.get_remote_ref(Path("/test/repo"), "origin", "missing")

        assert result is None


def test_get_remote_ref_handles_multiple_lines() -> None:
    """get_remote_ref returns SHA from first line when multiple refs match."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="first111\trefs/heads/main\nsecond222\trefs/pull/1/head\n",
            returncode=0,
        )

        ops = RealGit()
        result = ops.remote.get_remote_ref(Path("/test/repo"), "origin", "main")

        assert result == "first111"


def test_get_local_tracking_ref_sha_returns_sha() -> None:
    """get_local_tracking_ref_sha returns SHA from git rev-parse output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="abc123def456789\n",
            returncode=0,
        )

        ops = RealGit()
        result = ops.remote.get_local_tracking_ref_sha(Path("/test/repo"), "origin", "main")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--verify", "origin/main"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["check"] is False
        assert result == "abc123def456789"


def test_get_local_tracking_ref_sha_returns_none_on_error() -> None:
    """get_local_tracking_ref_sha returns None when ref doesn't exist."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            returncode=128,
        )

        ops = RealGit()
        result = ops.remote.get_local_tracking_ref_sha(Path("/test/repo"), "origin", "nonexistent")

        assert result is None
