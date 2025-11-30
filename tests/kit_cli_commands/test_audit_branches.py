"""Tests for audit_branches kit CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.audit_branches import (
    AuditResult,
    BranchInfo,
    audit_branches_impl,
    get_commits_ahead,
    get_last_non_merge_commit,
    get_prs_for_repo,
    get_trunk_branch,
    get_worktrees,
    list_local_branches,
)


class TestGetTrunkBranch:
    """Tests for get_trunk_branch function."""

    def test_detects_main_from_remote_head(self, tmp_path: Path) -> None:
        """Should detect main branch from remote HEAD reference."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="refs/remotes/origin/main\n",
            )
            result = get_trunk_branch(tmp_path)
            assert result == "main"

    def test_detects_master_from_remote_head(self, tmp_path: Path) -> None:
        """Should detect master branch from remote HEAD reference."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="refs/remotes/origin/master\n",
            )
            result = get_trunk_branch(tmp_path)
            assert result == "master"

    def test_falls_back_to_main(self, tmp_path: Path) -> None:
        """Should fall back to main when remote HEAD not available."""
        with patch("subprocess.run") as mock_run:
            # First call: symbolic-ref fails
            # Second call: show-ref for main succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="abc123 refs/heads/main\n"),
            ]
            result = get_trunk_branch(tmp_path)
            assert result == "main"

    def test_falls_back_to_master(self, tmp_path: Path) -> None:
        """Should fall back to master when main doesn't exist."""
        with patch("subprocess.run") as mock_run:
            # symbolic-ref fails, main doesn't exist, master exists
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),
                MagicMock(returncode=1, stdout=""),  # main doesn't exist
                MagicMock(returncode=0, stdout="abc123 refs/heads/master\n"),
            ]
            result = get_trunk_branch(tmp_path)
            assert result == "master"


class TestListLocalBranches:
    """Tests for list_local_branches function."""

    def test_returns_branch_list(self, tmp_path: Path) -> None:
        """Should return list of branch names."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="main\nfeature-1\nfeature-2\n",
            )
            result = list_local_branches(tmp_path)
            assert result == ["main", "feature-1", "feature-2"]

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        """Should return empty list on git failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = list_local_branches(tmp_path)
            assert result == []

    def test_handles_empty_output(self, tmp_path: Path) -> None:
        """Should handle empty branch list."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = list_local_branches(tmp_path)
            assert result == []


class TestGetCommitsAhead:
    """Tests for get_commits_ahead function."""

    def test_returns_commit_count(self, tmp_path: Path) -> None:
        """Should return number of commits ahead."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5\n")
            result = get_commits_ahead(tmp_path, "main", "feature")
            assert result == 5

    def test_returns_zero_on_failure(self, tmp_path: Path) -> None:
        """Should return 0 on git failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = get_commits_ahead(tmp_path, "main", "feature")
            assert result == 0

    def test_returns_zero_on_invalid_output(self, tmp_path: Path) -> None:
        """Should return 0 on non-numeric output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not-a-number\n")
            result = get_commits_ahead(tmp_path, "main", "feature")
            assert result == 0


class TestGetLastNonMergeCommit:
    """Tests for get_last_non_merge_commit function."""

    def test_returns_commit_info(self, tmp_path: Path) -> None:
        """Should return sha, date, and message."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123|2024-01-15T10:30:00+00:00|Fix bug in login\n",
            )
            sha, date, message = get_last_non_merge_commit(tmp_path, "feature")
            assert sha == "abc123"
            assert date == "2024-01-15T10:30:00+00:00"
            assert message == "Fix bug in login"

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        """Should return None values on git failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            sha, date, message = get_last_non_merge_commit(tmp_path, "feature")
            assert sha is None
            assert date is None
            assert message is None

    def test_handles_message_with_pipe(self, tmp_path: Path) -> None:
        """Should handle commit messages containing pipe characters."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123|2024-01-15T10:30:00+00:00|Fix bug | add tests\n",
            )
            sha, date, message = get_last_non_merge_commit(tmp_path, "feature")
            assert sha == "abc123"
            assert date == "2024-01-15T10:30:00+00:00"
            assert message == "Fix bug | add tests"


class TestGetWorktrees:
    """Tests for get_worktrees function."""

    def test_returns_worktree_mapping(self, tmp_path: Path) -> None:
        """Should return mapping of branch to worktree path."""
        worktree_output = """worktree /repo
branch refs/heads/main

worktree /repo/.worktrees/feature
branch refs/heads/feature
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=worktree_output)
            result = get_worktrees(tmp_path)
            assert result == {
                "main": "/repo",
                "feature": "/repo/.worktrees/feature",
            }

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        """Should return empty dict on git failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = get_worktrees(tmp_path)
            assert result == {}


class TestGetPrsForRepo:
    """Tests for get_prs_for_repo function."""

    def test_returns_pr_info(self, tmp_path: Path) -> None:
        """Should return PR info for branches."""
        pr_json = """[
            {"number": 123, "state": "MERGED", "headRefName": "feature-1", "title": "Add feature"},
            {"number": 456, "state": "OPEN", "headRefName": "feature-2", "title": "WIP feature"},
            {"number": 789, "state": "CLOSED", "headRefName": "feature-3", "title": "Old feature"}
        ]"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
            result = get_prs_for_repo(tmp_path)
            assert result == {
                "feature-1": ("MERGED", 123, "Add feature"),
                "feature-2": ("OPEN", 456, "WIP feature"),
                "feature-3": ("CLOSED", 789, "Old feature"),
            }

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        """Should return empty dict on gh CLI failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = get_prs_for_repo(tmp_path)
            assert result == {}

    def test_returns_empty_on_invalid_json(self, tmp_path: Path) -> None:
        """Should return empty dict on invalid JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not json")
            result = get_prs_for_repo(tmp_path)
            assert result == {}

    def test_keeps_first_pr_for_branch(self, tmp_path: Path) -> None:
        """Should keep only first PR for each branch (most recent)."""
        pr_json = """[
            {"number": 456, "state": "OPEN", "headRefName": "feature", "title": "Second PR"},
            {"number": 123, "state": "MERGED", "headRefName": "feature", "title": "First PR"}
        ]"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=pr_json)
            result = get_prs_for_repo(tmp_path)
            # Should keep the first one (456) since it appears first in list
            assert result == {"feature": ("OPEN", 456, "Second PR")}


class TestAuditBranchesImpl:
    """Tests for audit_branches_impl function."""

    def test_returns_branch_info(self, tmp_path: Path) -> None:
        """Should return audit result with branch info."""
        with patch.multiple(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.audit_branches",
            get_trunk_branch=MagicMock(return_value="main"),
            list_local_branches=MagicMock(return_value=["main", "feature"]),
            get_worktrees=MagicMock(return_value={"main": "/repo"}),
            get_prs_for_repo=MagicMock(return_value={"feature": ("OPEN", 123, "My PR")}),
            get_commits_ahead=MagicMock(return_value=3),
            get_last_non_merge_commit=MagicMock(
                return_value=("abc123", "2024-01-15T10:00:00+00:00", "Add feature")
            ),
        ):
            result = audit_branches_impl(tmp_path)

            assert result.success is True
            assert result.trunk_branch == "main"
            assert len(result.branches) == 2

            # Check main branch
            main_branch = next(b for b in result.branches if b.name == "main")
            assert main_branch.is_trunk is True
            assert main_branch.commits_ahead == 0  # Trunk is always 0
            assert main_branch.worktree_path == "/repo"

            # Check feature branch
            feature_branch = next(b for b in result.branches if b.name == "feature")
            assert feature_branch.is_trunk is False
            assert feature_branch.commits_ahead == 3
            assert feature_branch.pr_state == "OPEN"
            assert feature_branch.pr_number == 123
            assert feature_branch.pr_title == "My PR"

    def test_handles_empty_branch_list(self, tmp_path: Path) -> None:
        """Should handle repository with no branches."""
        with patch.multiple(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.audit_branches",
            get_trunk_branch=MagicMock(return_value="main"),
            list_local_branches=MagicMock(return_value=[]),
            get_worktrees=MagicMock(return_value={}),
            get_prs_for_repo=MagicMock(return_value={}),
        ):
            result = audit_branches_impl(tmp_path)

            assert result.success is True
            assert result.branches == []
            assert "No local branches found" in result.errors

    def test_handles_branch_without_pr(self, tmp_path: Path) -> None:
        """Should handle branches without PRs."""
        with patch.multiple(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.audit_branches",
            get_trunk_branch=MagicMock(return_value="main"),
            list_local_branches=MagicMock(return_value=["main", "no-pr-branch"]),
            get_worktrees=MagicMock(return_value={}),
            get_prs_for_repo=MagicMock(return_value={}),
            get_commits_ahead=MagicMock(return_value=5),
            get_last_non_merge_commit=MagicMock(return_value=(None, None, None)),
        ):
            result = audit_branches_impl(tmp_path)

            assert result.success is True
            no_pr_branch = next(b for b in result.branches if b.name == "no-pr-branch")
            assert no_pr_branch.pr_state == "NONE"
            assert no_pr_branch.pr_number is None
            assert no_pr_branch.pr_title is None

    def test_handles_mixed_branches(self, tmp_path: Path) -> None:
        """Should handle mix of merged, open, closed, and no-PR branches."""
        with patch.multiple(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.audit_branches",
            get_trunk_branch=MagicMock(return_value="main"),
            list_local_branches=MagicMock(
                return_value=["main", "merged-branch", "open-branch", "closed-branch", "no-pr"]
            ),
            get_worktrees=MagicMock(
                return_value={"main": "/repo", "open-branch": "/repo/.wt/open"}
            ),
            get_prs_for_repo=MagicMock(
                return_value={
                    "merged-branch": ("MERGED", 100, "Merged PR"),
                    "open-branch": ("OPEN", 200, "Open PR"),
                    "closed-branch": ("CLOSED", 300, "Closed PR"),
                }
            ),
            get_commits_ahead=MagicMock(side_effect=[0, 5, 10, 2]),
            get_last_non_merge_commit=MagicMock(
                return_value=("sha", "2024-01-01T00:00:00Z", "commit msg")
            ),
        ):
            result = audit_branches_impl(tmp_path)

            assert result.success is True
            assert len(result.branches) == 5

            # Check each category
            merged = next(b for b in result.branches if b.name == "merged-branch")
            assert merged.pr_state == "MERGED"

            open_b = next(b for b in result.branches if b.name == "open-branch")
            assert open_b.pr_state == "OPEN"
            assert open_b.worktree_path == "/repo/.wt/open"

            closed = next(b for b in result.branches if b.name == "closed-branch")
            assert closed.pr_state == "CLOSED"

            no_pr = next(b for b in result.branches if b.name == "no-pr")
            assert no_pr.pr_state == "NONE"


class TestBranchInfoDataclass:
    """Tests for BranchInfo dataclass."""

    def test_creates_branch_info(self) -> None:
        """Should create BranchInfo with all fields."""
        info = BranchInfo(
            name="feature",
            commits_ahead=5,
            pr_state="OPEN",
            pr_number=123,
            pr_title="My Feature",
            last_non_merge_commit_date="2024-01-15T10:00:00Z",
            last_non_merge_commit_sha="abc123",
            last_non_merge_commit_message="Add feature",
            worktree_path="/repo/.wt/feature",
            is_trunk=False,
        )
        assert info.name == "feature"
        assert info.commits_ahead == 5
        assert info.pr_state == "OPEN"
        assert info.pr_number == 123


class TestAuditResultDataclass:
    """Tests for AuditResult dataclass."""

    def test_creates_audit_result(self) -> None:
        """Should create AuditResult with all fields."""
        result = AuditResult(
            success=True,
            trunk_branch="main",
            branches=[],
            errors=[],
        )
        assert result.success is True
        assert result.trunk_branch == "main"
        assert result.branches == []
        assert result.errors == []
