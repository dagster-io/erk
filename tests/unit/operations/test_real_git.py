"""Unit tests for RealGit with mocked subprocess calls.

These tests verify that RealGit correctly constructs subprocess commands
for external tools (git) without actually executing them.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_shared.git.real import RealGit


def test_list_remote_branches() -> None:
    """Test git branch -r with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return sample remote branches
        mock_run.return_value = MagicMock(
            stdout="origin/main\norigin/feature-1\norigin/feature-2\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGit()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "branch", "-r", "--format=%(refname:short)"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True

        # Assert: Verify parsing
        assert branches == ["origin/main", "origin/feature-1", "origin/feature-2"]


def test_list_remote_branches_empty() -> None:
    """Test git branch -r returns empty list when no remotes."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return empty output
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        # Act: Call the method
        ops = RealGit()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify empty list returned
        assert branches == []


def test_list_remote_branches_strips_whitespace() -> None:
    """Test git branch -r strips whitespace from branch names."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock with extra whitespace
        mock_run.return_value = MagicMock(
            stdout="  origin/main  \n  origin/feature  \n\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGit()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify whitespace stripped
        assert branches == ["origin/main", "origin/feature"]


def test_branch_exists_on_remote_when_exists() -> None:
    """Test git ls-remote returns True when branch exists on remote."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return branch ref (branch exists)
        mock_run.return_value = MagicMock(
            stdout="abc123def456\trefs/heads/feature-branch\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGit()
        exists = ops.branch_exists_on_remote(Path("/test/repo"), "origin", "feature-branch")

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "ls-remote", "origin", "feature-branch"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is False

        # Assert: Verify result
        assert exists is True


def test_branch_exists_on_remote_when_not_exists() -> None:
    """Test git ls-remote returns False when branch doesn't exist on remote."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return empty output (branch doesn't exist)
        mock_run.return_value = MagicMock(
            stdout="",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGit()
        exists = ops.branch_exists_on_remote(Path("/test/repo"), "origin", "nonexistent-branch")

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "ls-remote", "origin", "nonexistent-branch"]

        # Assert: Verify result
        assert exists is False


def test_branch_exists_on_remote_with_whitespace() -> None:
    """Test git ls-remote handles whitespace correctly."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock with whitespace
        mock_run.return_value = MagicMock(
            stdout="  abc123def456\trefs/heads/feature-branch  \n\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGit()
        exists = ops.branch_exists_on_remote(Path("/test/repo"), "origin", "feature-branch")

        # Assert: Verify result (whitespace stripped before checking)
        assert exists is True
