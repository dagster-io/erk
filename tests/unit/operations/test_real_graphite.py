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


def test_real_graphite_is_branch_tracked_returns_true_for_tracked() -> None:
    """Test is_branch_tracked returns True when gt returns exit code 0."""
    with patch("erk_shared.gateway.graphite.real.subprocess.run") as mock_run:
        # Mock exit code 0 (branch is tracked)
        mock_run.return_value = MagicMock(returncode=0)

        ops = RealGraphite()
        result = ops.is_branch_tracked(Path("/test"), "feature-branch")

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "branch", "info", "feature-branch", "--quiet"]
        assert call_args[1]["cwd"] == Path("/test")
        assert call_args[1]["check"] is False


def test_real_graphite_is_branch_tracked_returns_false_for_untracked() -> None:
    """Test is_branch_tracked returns False when gt returns non-zero exit code."""
    with patch("erk_shared.gateway.graphite.real.subprocess.run") as mock_run:
        # Mock exit code 1 (branch is untracked)
        mock_run.return_value = MagicMock(returncode=1)

        ops = RealGraphite()
        result = ops.is_branch_tracked(Path("/test"), "untracked-branch")

        assert result is False
        mock_run.assert_called_once()


def test_real_graphite_is_branch_tracked_constructs_correct_command() -> None:
    """Test is_branch_tracked passes correct arguments to subprocess."""
    with patch("erk_shared.gateway.graphite.real.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        ops = RealGraphite()
        ops.is_branch_tracked(Path("/repo/root"), "my-feature")

        mock_run.assert_called_once_with(
            ["gt", "branch", "info", "my-feature", "--quiet"],
            cwd=Path("/repo/root"),
            capture_output=True,
            text=True,
            check=False,
        )


def test_submit_stack_invalidates_branches_cache() -> None:
    """Verify submit_stack() invalidates the branches cache.

    This is a regression test for a bug where gt ls showed no branches
    immediately after erk plan submit, because _branches_cache wasn't
    invalidated after gt submit updated .graphite_cache_persist.
    """
    with patch("erk_shared.gateway.graphite.real.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        ops = RealGraphite()
        # Pre-populate cache with stale data
        ops._branches_cache = {"stale": "data"}  # type: ignore[assignment]

        ops.submit_stack(Path("/test"))

        # Cache should be invalidated after submit_stack
        assert ops._branches_cache is None


def test_sync_invalidates_branches_cache() -> None:
    """Verify sync() invalidates the branches cache."""
    with patch("subprocess.run"):
        ops = RealGraphite()
        ops._branches_cache = {"stale": "data"}  # type: ignore[assignment]

        ops.sync(Path("/test"), force=False, quiet=False)

        assert ops._branches_cache is None


def test_restack_invalidates_branches_cache() -> None:
    """Verify restack() invalidates the branches cache."""
    with patch("subprocess.run"):
        ops = RealGraphite()
        ops._branches_cache = {"stale": "data"}  # type: ignore[assignment]

        ops.restack(Path("/test"), no_interactive=True, quiet=False)

        assert ops._branches_cache is None


def test_continue_restack_invalidates_branches_cache() -> None:
    """Verify continue_restack() invalidates the branches cache."""
    with patch("subprocess.run"):
        ops = RealGraphite()
        ops._branches_cache = {"stale": "data"}  # type: ignore[assignment]

        ops.continue_restack(Path("/test"))

        assert ops._branches_cache is None
