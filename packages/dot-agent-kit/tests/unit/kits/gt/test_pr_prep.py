"""Tests for pr_prep kit CLI command using fake ops."""

from pathlib import Path
from unittest.mock import patch

from erk_shared.integrations.gt.kit_cli_commands.gt.pr_prep import (
    PrepError,
    PrepResult,
    execute_prep,
)

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


class TestPrepExecution:
    """Tests for prep phase execution logic."""

    def test_prep_gt_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when Graphite CLI is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gt_not_authenticated"
        assert "Graphite CLI (gt) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gt auth' to authenticate with Graphite"
        assert result.details["authenticated"] is False

    def test_prep_gh_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when GitHub CLI is not authenticated (gt is authenticated)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gh_unauthenticated()
        )

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "GitHub CLI (gh) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gh auth login' to authenticate with GitHub"
        assert result.details["authenticated"] is False

    def test_prep_gt_checked_before_gh(self, tmp_path: Path) -> None:
        """Test that Graphite authentication is checked before GitHub."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
            .with_gh_unauthenticated()
        )

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        # When both are unauthenticated, gt should be reported first
        assert isinstance(result, PrepError)
        assert result.error_type == "gt_not_authenticated"

    def test_prep_no_branch(self, tmp_path: Path) -> None:
        """Test error when current branch cannot be determined."""
        ops = FakeGtKitOps()
        # Set current_branch to None to simulate failure
        from dataclasses import replace

        ops.git()._state = replace(ops.git().get_state(), current_branch="")  # type: ignore[attr-defined]

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "Could not determine current branch" in result.message

    def test_prep_no_parent_branch(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        # Create a fresh FakeGtKitOps without using with_branch
        # to avoid having the parent relationship set up in main_graphite
        ops = FakeGtKitOps()
        # Manually set just the current branch without any parent relationship
        from dataclasses import replace

        git_state = ops.git().get_state()  # type: ignore[attr-defined]
        ops.git()._state = replace(  # type: ignore[attr-defined]
            git_state, current_branch="orphan-branch", commits=["commit-1"]
        )
        ops.github().set_current_branch("orphan-branch")
        # main_graphite has no branches tracked, so get_parent_branch returns None

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message
        assert result.details["branch_name"] == "orphan-branch"

    def test_prep_no_commits(self, tmp_path: Path) -> None:
        """Test error when branch has no commits."""
        ops = FakeGtKitOps().with_branch("empty-branch", parent="main").with_commits(0)

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_commits"
        assert "No commits found in branch" in result.message
        assert result.details["branch_name"] == "empty-branch"
        assert result.details["parent_branch"] == "main"

    def test_prep_single_commit_no_squash(self, tmp_path: Path) -> None:
        """Test prep with single commit (no squash needed)."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            with patch("subprocess.run") as mock_run:
                mock_write.return_value = tmp_path / "fake.diff"
                # Mock git diff command
                mock_run.return_value.stdout = "diff content here\n"
                mock_run.return_value.returncode = 0

                result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_prep_multiple_commits_squash(self, tmp_path: Path) -> None:
        """Test prep with multiple commits (should squash)."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(3)

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            with patch("subprocess.run") as mock_run:
                mock_write.return_value = tmp_path / "fake.diff"
                # Mock git diff command
                mock_run.return_value.stdout = "diff content here\n"
                mock_run.return_value.returncode = 0

                result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
        assert result.commit_count == 3
        assert result.squashed is True
        assert "Squashed 3 commits into 1" in result.message

    def test_prep_restack_conflict_detected(self, tmp_path: Path) -> None:
        """Test error when restack conflicts are detected."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_conflict()
        )

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "restack_conflict"
        assert "Restack conflicts detected" in result.message
        assert "Run 'gt restack' to resolve conflicts first" in result.message

    def test_prep_squash_conflict_detected(self, tmp_path: Path) -> None:
        """Test error when squash conflicts are detected."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_conflict()
        )

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            mock_write.return_value = tmp_path / "fake.diff"
            result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "squash_conflict"
        assert "Merge conflicts detected while squashing commits" in result.message

    def test_prep_writes_diff_to_scratch(self, tmp_path: Path) -> None:
        """Test that prep writes diff to scratch file."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        expected_diff_path = tmp_path / "pr-prep-diff-test-session.diff"

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            with patch("subprocess.run") as mock_run:
                mock_write.return_value = expected_diff_path
                # Mock git diff command
                expected_diff_content = "diff --git a/file.py b/file.py\n+new line\n"
                mock_run.return_value.stdout = expected_diff_content
                mock_run.return_value.returncode = 0

                result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.diff_file == str(expected_diff_path)

        # Verify write_scratch_file was called with correct args
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args.kwargs["session_id"] == "test-session"
        assert call_args.kwargs["prefix"] == "pr-prep-diff-"
        assert call_args.kwargs["suffix"] == ".diff"
        # Verify diff content was passed
        assert expected_diff_content in call_args.args[0]

    def test_prep_success_with_repo_metadata(self, tmp_path: Path) -> None:
        """Test that prep returns correct repo metadata."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(2)

        with patch("erk_shared.scratch.scratch.write_scratch_file") as mock_write:
            with patch("subprocess.run") as mock_run:
                mock_write.return_value = tmp_path / "fake.diff"
                mock_run.return_value.stdout = "diff content\n"
                mock_run.return_value.returncode = 0

                result = execute_prep(session_id="test-session", ops=ops)

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.repo_root == "/fake/repo/root"
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
