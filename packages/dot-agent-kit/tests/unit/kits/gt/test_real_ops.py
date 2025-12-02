"""Unit tests for real_ops.py subprocess integration with mocked subprocess.

These tests verify that real subprocess-based implementations construct commands
correctly and parse outputs properly. All subprocess calls are mocked to ensure
fast execution. For integration tests with real subprocess calls, see
tests/integration/kits/gt/test_real_git_ops.py.

Test organization:
- TestRealGitHubGtKitOps: GitHub operations (4 methods, mocked subprocess)
- TestRealGtKitOps: Composite operations (2 accessor methods)

Note: Git operations are now tested via the core Git interface in erk_shared.git.
"""

import subprocess
from unittest.mock import Mock, patch

from erk_shared.integrations.gt import (
    RealGitHubGtKit,
    RealGtKit,
)


class TestRealGitHubGtKitOps:
    """Unit tests for RealGitHubGtKit with mocked subprocess calls."""

    def test_get_pr_info(self) -> None:
        """Test get_pr_info returns tuple or None."""
        # Test success case with real JSON response format
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '{"number":467,"url":"https://github.com/dagster-io/workstack/pull/467"}'
        )
        mock_result.stderr = ""

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKit()
            result = ops.get_pr_info()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gh", "pr", "view", "--json", "number,url"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            # Verify return type matches interface contract
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
            pr_number, pr_url = result
            assert pr_number == 467
            assert isinstance(pr_number, int)
            assert pr_url == "https://github.com/dagster-io/workstack/pull/467"
            assert isinstance(pr_url, str)

        # Test failure case (no PR found)
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKit()
            result = ops.get_pr_info()
            assert result is None

    def test_get_pr_info_timeout(self) -> None:
        """Test get_pr_info handles TimeoutExpired exception correctly."""
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["gh", "pr", "view"], timeout=10),
        ):
            ops = RealGitHubGtKit()
            result = ops.get_pr_info()

            # Verify timeout returns None (same as PR not found)
            assert result is None

    def test_get_pr_state(self) -> None:
        """Test get_pr_state returns tuple or None."""
        # Test success case with real JSON response format
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"number":467,"state":"OPEN"}'
        mock_result.stderr = ""

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKit()
            result = ops.get_pr_state()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gh", "pr", "view", "--json", "state,number"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            # Verify return type matches interface contract
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
            pr_number, pr_state = result
            assert pr_number == 467
            assert isinstance(pr_number, int)
            assert pr_state == "OPEN"
            assert isinstance(pr_state, str)

        # Test failure case (no PR found)
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKit()
            result = ops.get_pr_state()
            assert result is None

    def test_update_pr_metadata(self) -> None:
        """Test update_pr_metadata returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "erk_shared.integrations.gt.real._run_subprocess_with_timeout",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKit()
            result = ops.update_pr_metadata("Test Title", "Test Body")

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gh", "pr", "edit", "--title", "Test Title", "--body", "Test Body"],
                timeout=30,
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real._run_subprocess_with_timeout",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKit()
            result = ops.update_pr_metadata("Title", "Body")
            assert result is False

    def test_update_pr_metadata_timeout(self) -> None:
        """Test update_pr_metadata handles timeout correctly."""
        with patch(
            "erk_shared.integrations.gt.real._run_subprocess_with_timeout",
            return_value=None,  # Helper returns None on timeout
        ):
            ops = RealGitHubGtKit()
            result = ops.update_pr_metadata("Test Title", "Test Body")

            # Verify timeout returns False (indicates failure)
            assert result is False

    def test_merge_pr(self) -> None:
        """Test merge_pr returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKit()
            result = ops.merge_pr()

            # Verify correct command was called (squash merge)
            mock_run.assert_called_once_with(
                ["gh", "pr", "merge", "-s"], capture_output=True, text=True, check=False
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKit()
            result = ops.merge_pr()
            assert result is False


class TestRealGtKitOps:
    """Unit tests for RealGtKit composite operations."""

    def test_git(self) -> None:
        """Test git() returns RealGit instance."""
        ops = RealGtKit()

        # Get git operations interface
        git_ops = ops.git()

        # Verify return type matches interface contract
        from erk_shared.git.real import RealGit

        assert isinstance(git_ops, RealGit)

    def test_github(self) -> None:
        """Test github() returns RealGitHubGtKit instance."""
        ops = RealGtKit()

        # Get github operations interface
        github_ops = ops.github()

        # Verify return type matches interface contract
        assert isinstance(github_ops, RealGitHubGtKit)
