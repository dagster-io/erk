"""Integration tests for RealGit.is_branch_diverged_from_remote with mocking.

Layer 2 tests: Mock subprocess calls to verify correct git commands
are constructed and output is parsed correctly.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_shared.git.real import RealGit


class TestIsBranchDivergedFromRemote:
    """Tests for is_branch_diverged_from_remote method."""

    def test_calls_rev_parse_to_check_remote_branch_exists(self) -> None:
        """Verifies git rev-parse is called to check remote branch exists."""
        cwd = Path("/test/repo")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "2\n"

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "3\n"

        side_effects = [mock_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            git = RealGit()
            git.is_branch_diverged_from_remote(cwd, "feature", "origin")

            # First call should verify remote branch exists
            first_call = mock_run.call_args_list[0]
            expected = ["git", "rev-parse", "--verify", "origin/feature"]
            assert first_call[0][0] == expected
            assert first_call[1]["cwd"] == cwd

    def test_returns_false_when_remote_branch_does_not_exist(self) -> None:
        """Returns (False, 0, 0) when remote branch doesn't exist."""
        cwd = Path("/test/repo")
        mock_result = MagicMock()
        mock_result.returncode = 128  # git rev-parse fails for non-existent ref

        with patch("subprocess.run", return_value=mock_result):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is False
            assert ahead == 0
            assert behind == 0

    def test_calls_rev_list_for_ahead_and_behind_counts(self) -> None:
        """Verifies correct rev-list commands for ahead/behind counts."""
        cwd = Path("/test/repo")

        # rev-parse succeeds
        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        # ahead count
        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "5\n"

        # behind count
        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "3\n"

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            git = RealGit()
            git.is_branch_diverged_from_remote(cwd, "my-branch", "origin")

            # Second call: ahead count (remote..local)
            ahead_call = mock_run.call_args_list[1]
            expected_ahead = [
                "git",
                "rev-list",
                "--count",
                "origin/my-branch..my-branch",
            ]
            assert ahead_call[0][0] == expected_ahead
            assert ahead_call[1]["cwd"] == cwd

            # Third call: behind count (local..remote)
            behind_call = mock_run.call_args_list[2]
            expected_behind = [
                "git",
                "rev-list",
                "--count",
                "my-branch..origin/my-branch",
            ]
            assert behind_call[0][0] == expected_behind
            assert behind_call[1]["cwd"] == cwd

    def test_returns_diverged_true_when_both_ahead_and_behind(self) -> None:
        """Branch is diverged when it has commits both ahead and behind."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "2\n"

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "3\n"

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is True
            assert ahead == 2
            assert behind == 3

    def test_returns_diverged_false_when_only_ahead(self) -> None:
        """Branch is not diverged when it's only ahead (no remote commits to pull)."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "5\n"

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "0\n"

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is False
            assert ahead == 5
            assert behind == 0

    def test_returns_diverged_false_when_only_behind(self) -> None:
        """Branch is not diverged when it's only behind (fast-forward possible)."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "0\n"

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "4\n"

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is False
            assert ahead == 0
            assert behind == 4

    def test_returns_diverged_false_when_in_sync(self) -> None:
        """Branch is not diverged when it's in sync with remote."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "0\n"

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "0\n"

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is False
            assert ahead == 0
            assert behind == 0

    def test_handles_rev_list_failure_gracefully(self) -> None:
        """Returns 0 counts if rev-list commands fail."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        # Both rev-list commands fail
        ahead_result = MagicMock()
        ahead_result.returncode = 1
        ahead_result.stdout = ""

        behind_result = MagicMock()
        behind_result.returncode = 1
        behind_result.stdout = ""

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is False
            assert ahead == 0
            assert behind == 0

    def test_strips_whitespace_from_count_output(self) -> None:
        """Correctly parses counts with trailing newlines/whitespace."""
        cwd = Path("/test/repo")

        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "abc123\n"

        ahead_result = MagicMock()
        ahead_result.returncode = 0
        ahead_result.stdout = "  10  \n"  # Extra whitespace

        behind_result = MagicMock()
        behind_result.returncode = 0
        behind_result.stdout = "\n7\n\n"  # Multiple newlines

        side_effects = [rev_parse_result, ahead_result, behind_result]
        with patch("subprocess.run", side_effect=side_effects):
            git = RealGit()
            result = git.is_branch_diverged_from_remote(cwd, "feature", "origin")
            is_diverged, ahead, behind = result

            assert is_diverged is True
            assert ahead == 10
            assert behind == 7
