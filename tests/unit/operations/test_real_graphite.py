"""Unit tests for RealGraphite with mocked subprocess calls.

These tests verify that RealGraphite correctly constructs subprocess commands
for external tools (gt) without actually executing them.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_shared.gateway.graphite.real import RealGraphite


def test_real_graphite_ops_sync() -> None:
    """Test gt sync with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphite()
        ops.sync(Path("/test"), force=False, quiet=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync"]
        assert call_args[1]["cwd"] == Path("/test")
        assert call_args[1]["check"] is True


def test_real_graphite_ops_sync_with_force() -> None:
    """Test gt sync with force flag."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphite()
        ops.sync(Path("/test"), force=True, quiet=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "-f"]


def test_real_graphite_ops_sync_with_quiet() -> None:
    """Test gt sync with quiet flag."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphite()
        ops.sync(Path("/test"), force=False, quiet=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "--quiet"]


def test_real_graphite_ops_sync_with_force_and_quiet() -> None:
    """Test gt sync with both force and quiet flags."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphite()
        ops.sync(Path("/test"), force=True, quiet=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "-f", "--quiet"]


def test_real_graphite_ops_submit_branch() -> None:
    """Test gt submit with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        # Mock the return value to have stderr attribute
        mock_run.return_value = MagicMock(stderr="")

        ops = RealGraphite()
        ops.submit_branch(Path("/test"), "feat-1", quiet=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected = ["gt", "submit", "--branch", "feat-1", "--no-edit", "--no-interactive"]
        assert call_args[0][0] == expected
        assert call_args[1]["cwd"] == Path("/test")
        assert call_args[1]["check"] is True


def test_real_graphite_ops_submit_branch_with_quiet() -> None:
    """Test gt submit with quiet flag."""
    with patch("subprocess.run") as mock_run:
        # Mock the return value to have stderr attribute
        mock_run.return_value = MagicMock(stderr="")

        ops = RealGraphite()
        ops.submit_branch(Path("/test"), "feat-2", quiet=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected = [
            "gt",
            "submit",
            "--branch",
            "feat-2",
            "--no-edit",
            "--no-interactive",
            "--quiet",
        ]
        assert call_args[0][0] == expected


def test_real_graphite_ops_submit_branch_stderr_handling() -> None:
    """Test that stderr is displayed in verbose mode after successful execution."""
    with patch("subprocess.run") as mock_run, patch("click.echo") as mock_echo:
        # Mock the return value to have stderr content
        mock_run.return_value = MagicMock(stderr="Submitted PR #123\n")

        ops = RealGraphite()
        ops.submit_branch(Path("/test"), "feat-3", quiet=False)

        # Verify subprocess was called
        mock_run.assert_called_once()

        # Verify stderr was echoed in verbose mode (quiet=False)
        mock_echo.assert_called_once_with("Submitted PR #123\n", nl=False, err=True, color=None)


def test_real_graphite_ops_submit_branch_quiet_no_stderr_output() -> None:
    """Test that stderr is NOT displayed when quiet=True."""
    with patch("subprocess.run") as mock_run, patch("click.echo") as mock_echo:
        # Mock the return value to have stderr content
        mock_run.return_value = MagicMock(stderr="Submitted PR #123\n")

        ops = RealGraphite()
        ops.submit_branch(Path("/test"), "feat-4", quiet=True)

        # Verify subprocess was called
        mock_run.assert_called_once()

        # Verify stderr was NOT echoed in quiet mode
        mock_echo.assert_not_called()
