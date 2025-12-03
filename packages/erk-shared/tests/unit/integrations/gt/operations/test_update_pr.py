"""Tests for execute_update_pr operation with event assertions.

Tests the update-pr workflow which stages, commits, restacks, and submits changes.
"""

from pathlib import Path

from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.operations.update_pr import execute_update_pr

from tests.unit.integrations.gt.operations.conftest import (
    collect_events,
    has_event_containing,
)


class TestUpdatePrSuccess:
    """Tests for successful update-pr execution."""

    def test_success_with_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test successful update when there are uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
            .with_pr(123)
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["pr_number"] == 123
        assert "pr_url" in result

        # Assert key events for uncommitted changes path
        assert has_event_containing(events, "Staging uncommitted changes")
        assert has_event_containing(events, "Committing changes")
        assert has_event_containing(events, "Changes committed")
        assert has_event_containing(events, "Restacking branch")
        assert has_event_containing(events, "Branch restacked")
        assert has_event_containing(events, "Submitting PR update")
        assert has_event_containing(events, "updated successfully")

    def test_success_without_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test successful update when there are no uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(456)
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["pr_number"] == 456

        # Should NOT have staging/committing events
        assert not has_event_containing(events, "Staging uncommitted changes")
        assert not has_event_containing(events, "Committing changes")
        # But should have restack and submit
        assert has_event_containing(events, "Restacking branch")
        assert has_event_containing(events, "Submitting PR update")


class TestUpdatePrStageErrors:
    """Tests for staging-related failures."""

    def test_add_failure(self, tmp_path: Path) -> None:
        """Test error when git add fails."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
            .with_add_failure()
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "Failed to stage changes" in result["error"]

        # Should have started staging
        assert has_event_containing(events, "Staging uncommitted changes")


class TestUpdatePrRestackErrors:
    """Tests for restack-related failures."""

    def test_restack_conflict(self, tmp_path: Path) -> None:
        """Test error when restack has conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_restack_conflict()
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result.get("error_type") == "restack_conflict"
        assert "Merge conflict detected" in result["error"]
        assert "details" in result

        # Should have started restack
        assert has_event_containing(events, "Restacking branch")

    def test_restack_failure(self, tmp_path: Path) -> None:
        """Test error when restack fails for non-conflict reason."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_restack_failure(stderr="Something went wrong")
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result.get("error_type") == "restack_failed"
        assert "Failed to restack branch" in result["error"]


class TestUpdatePrSubmitErrors:
    """Tests for submit-related failures."""

    def test_remote_divergence(self, tmp_path: Path) -> None:
        """Test error when branch has diverged from remote."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_remote_divergence()
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result.get("error_type") == "remote_divergence"
        assert "diverged from remote" in result["error"]
        assert "Do NOT auto-sync" in result["error"]

        # Should have gotten to submit
        assert has_event_containing(events, "Submitting PR update")

    def test_submit_failure(self, tmp_path: Path) -> None:
        """Test error when submit fails for generic reason."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_submit_failure(stderr="Something went wrong")
        )

        events, result = collect_events(execute_update_pr(ops, tmp_path))

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "Failed to submit update" in result["error"]
