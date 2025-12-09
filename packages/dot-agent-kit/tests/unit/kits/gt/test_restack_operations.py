"""Tests for restack operations using fake ops.

Tests the three-phase restack flow: preflight, continue, finalize.
"""

from pathlib import Path

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.restack_continue import execute_restack_continue
from erk_shared.integrations.gt.operations.restack_finalize import execute_restack_finalize
from erk_shared.integrations.gt.operations.restack_preflight import execute_restack_preflight
from erk_shared.integrations.gt.types import (
    RestackContinueSuccess,
    RestackFinalizeError,
    RestackFinalizeSuccess,
    RestackPreflightError,
    RestackPreflightSuccess,
)

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


class TestRestackPreflight:
    """Tests for restack preflight operation."""

    def test_successful_restack_no_conflicts(self, tmp_path: Path) -> None:
        """Test successful restack with no conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_rebase_in_progress(False)
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightSuccess)
        assert result.success is True
        assert result.has_conflicts is False
        assert result.conflicts == []
        assert result.branch_name == "feature-branch"

    def test_restack_with_conflicts(self, tmp_path: Path) -> None:
        """Test restack that detects conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_conflicts(["file1.py", "file2.py"])
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightSuccess)
        assert result.success is True
        assert result.has_conflicts is True
        assert result.conflicts == ["file1.py", "file2.py"]
        assert result.branch_name == "feature-branch"

    def test_squash_failure_returns_error(self, tmp_path: Path) -> None:
        """Test error when squash fails."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_failure(stderr="Something went wrong")
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightError)
        assert result.success is False
        assert result.error_type == "squash_failed"

    def test_no_commits_returns_error(self, tmp_path: Path) -> None:
        """Test error when no commits to squash."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(0)
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightError)
        assert result.success is False
        assert result.error_type == "no_commits"

    def test_squash_conflict_returns_error(self, tmp_path: Path) -> None:
        """Test error when squash has conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_conflict()
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightError)
        assert result.success is False
        assert result.error_type == "squash_conflict"

    def test_dirty_working_tree_returns_error(self, tmp_path: Path) -> None:
        """Test error when working tree has uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_uncommitted_files(["modified.py"])
        )

        result = render_events(execute_restack_preflight(ops, tmp_path))

        assert isinstance(result, RestackPreflightError)
        assert result.success is False
        assert result.error_type == "dirty_working_tree"
        assert "uncommitted changes" in result.message


class TestRestackContinue:
    """Tests for restack continue operation."""

    def test_continue_restack_completes(self, tmp_path: Path) -> None:
        """Test continue when restack completes successfully."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_rebase_in_progress(False)
        )

        result = render_events(execute_restack_continue(ops, tmp_path, ["file1.py"]))

        assert isinstance(result, RestackContinueSuccess)
        assert result.success is True
        assert result.restack_complete is True
        assert result.has_conflicts is False

    def test_continue_with_new_conflicts(self, tmp_path: Path) -> None:
        """Test continue that encounters new conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_conflicts(["file3.py"])  # New conflict after continue
        )

        result = render_events(execute_restack_continue(ops, tmp_path, ["file1.py"]))

        assert isinstance(result, RestackContinueSuccess)
        assert result.success is True
        assert result.restack_complete is False
        assert result.has_conflicts is True
        assert result.conflicts == ["file3.py"]


class TestRestackFinalize:
    """Tests for restack finalize operation."""

    def test_finalize_success(self, tmp_path: Path) -> None:
        """Test successful finalize with clean state."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_rebase_in_progress(False)
            .with_clean_working_tree()
        )

        result = render_events(execute_restack_finalize(ops, tmp_path))

        assert isinstance(result, RestackFinalizeSuccess)
        assert result.success is True
        assert result.branch_name == "feature-branch"

    def test_finalize_fails_rebase_in_progress(self, tmp_path: Path) -> None:
        """Test finalize fails when rebase still in progress."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_rebase_in_progress(True)
        )

        result = render_events(execute_restack_finalize(ops, tmp_path))

        assert isinstance(result, RestackFinalizeError)
        assert result.success is False
        assert result.error_type == "rebase_still_in_progress"

    def test_finalize_fails_dirty_working_tree(self, tmp_path: Path) -> None:
        """Test finalize fails with uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_rebase_in_progress(False)
            .with_uncommitted_files(["modified.py"])
        )

        result = render_events(execute_restack_finalize(ops, tmp_path))

        assert isinstance(result, RestackFinalizeError)
        assert result.success is False
        assert result.error_type == "dirty_working_tree"
