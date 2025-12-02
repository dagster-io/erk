"""Unit tests for real_ops.py subprocess integration with mocked subprocess.

These tests verify that real subprocess-based implementations construct commands
correctly and parse outputs properly. All subprocess calls are mocked to ensure
fast execution. For integration tests with real subprocess calls, see
tests/integration/kits/gt/test_real_git_ops.py.

Test organization:
- TestRealGitGtKitOps: Git operations (6 methods, mocked subprocess)
- TestRealGitHubGtKitOps: GitHub operations (4 methods, mocked subprocess)
- TestRealGtKitOps: Composite operations (2 accessor methods)
"""

from unittest.mock import Mock, patch

from erk_shared.integrations.gt import (
    RealGitGtKit,
    RealGtKit,
)


class TestRealGitGtKitOps:
    """Unit tests for RealGitGtKit with mocked subprocess calls."""

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_get_current_branch(self, mock_run: Mock) -> None:
        """Test get_current_branch constructs command and parses output correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        branch_name = ops.get_current_branch()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "branch", "--show-current"]

        # Verify output parsing
        assert branch_name == "main"

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_has_uncommitted_changes_clean(self, mock_run: Mock) -> None:
        """Test has_uncommitted_changes returns False when repo is clean."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""  # Empty output = clean repo
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.has_uncommitted_changes()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "status", "--porcelain"]

        # Verify return value
        assert result is False

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_has_uncommitted_changes_dirty(self, mock_run: Mock) -> None:
        """Test has_uncommitted_changes returns True when repo has changes."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = " M file.txt\n"  # Modified file
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.has_uncommitted_changes()

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_add_all(self, mock_run: Mock) -> None:
        """Test add_all constructs command correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.add_all()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "add", "."]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_commit(self, mock_run: Mock) -> None:
        """Test commit constructs command with message correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.commit("Test commit message")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "commit", "-m", "Test commit message"]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_amend_commit(self, mock_run: Mock) -> None:
        """Test amend_commit constructs command with message correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.amend_commit("Amended message")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "commit", "--amend", "-m", "Amended message"]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_count_commits_in_branch(self, mock_run: Mock) -> None:
        """Test count_commits_in_branch constructs command and parses count."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "3\n"
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        count = ops.count_commits_in_branch("main")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "rev-list", "--count", "main..HEAD"]

        # Verify output parsing
        assert count == 3


class TestRealGtKitOps:
    """Unit tests for RealGtKit composite operations."""

    def test_git(self) -> None:
        """Test git() returns RealGitGtKit instance."""
        ops = RealGtKit()

        # Get git operations interface
        git_ops = ops.git()

        # Verify return type matches interface contract
        assert isinstance(git_ops, RealGitGtKit)

    def test_github(self) -> None:
        """Test github() returns a GitHub implementation."""
        from erk_shared.github.abc import GitHub

        ops = RealGtKit()

        # Get github operations interface
        github_ops = ops.github()

        # Verify return type matches interface contract
        assert isinstance(github_ops, GitHub)
