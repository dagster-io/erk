"""Tests for execute_prep operation with event assertions.

Tests the prep phase which checks auth, checks conflicts, squashes commits,
and extracts the diff for AI commit message generation.
"""

from pathlib import Path

from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.operations.prep import execute_prep
from erk_shared.integrations.gt.types import PrepError, PrepResult

from tests.unit.integrations.gt.operations.conftest import (
    collect_events,
    has_event_containing,
)


class TestPrepSuccessPath:
    """Tests for successful prep execution."""

    def test_success_with_squash(self, tmp_path: Path) -> None:
        """Test successful prep with multiple commits that get squashed."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.current_branch == "feature-branch"
        assert result.parent_branch == "main"
        assert result.commit_count == 3
        assert result.squashed is True
        assert "feature-branch" in result.message

        # Assert key events
        assert has_event_containing(events, "Authenticated as")
        assert has_event_containing(events, "No restack conflicts")
        assert has_event_containing(events, "Squashed")
        assert has_event_containing(events, "Diff retrieved")

    def test_success_without_squash(self, tmp_path: Path) -> None:
        """Test successful prep with single commit (no squash needed)."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepResult)
        assert result.success is True
        assert result.squashed is False
        assert result.commit_count == 1

        # Should NOT have squash event
        assert not has_event_containing(events, "Squashing")
        # But should have diff retrieved
        assert has_event_containing(events, "Diff retrieved")


class TestPrepAuthErrors:
    """Tests for authentication-related failures."""

    def test_gt_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when Graphite is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gt_not_authenticated"
        assert "Graphite CLI" in result.message

        # Should NOT have any authenticated event (failed before that)
        assert not has_event_containing(events, "Authenticated as")

    def test_gh_not_authenticated(self, tmp_path: Path) -> None:
        """Test error when GitHub is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gh_unauthenticated()
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "GitHub CLI" in result.message

        # Should have GT auth passed first
        assert has_event_containing(events, "Authenticated as")


class TestPrepBranchErrors:
    """Tests for branch-related failures."""

    def test_no_branch(self, tmp_path: Path) -> None:
        """Test error when current branch cannot be determined."""
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_no_branch()

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "Could not determine current branch" in result.message

        # Auth should have passed
        assert has_event_containing(events, "Authenticated as")

    def test_no_parent(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_orphan_branch("orphan-branch")

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message

        # Should have passed auth and gotten to branch lookup
        assert has_event_containing(events, "Authenticated as")


class TestPrepConflictErrors:
    """Tests for conflict-related failures."""

    def test_restack_conflict(self, tmp_path: Path) -> None:
        """Test error when restack has conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(2)
            .with_restack_conflict()
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "restack_conflict"
        assert "Restack conflicts detected" in result.message
        assert "details" in dir(result)
        assert result.details.get("branch_name") == "feature-branch"


class TestPrepCommitErrors:
    """Tests for commit-related failures."""

    def test_no_commits(self, tmp_path: Path) -> None:
        """Test error when branch has no commits ahead of parent."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(0)
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "no_commits"
        assert "No commits found" in result.message

        # Should have passed restack check
        assert has_event_containing(events, "No restack conflicts")


class TestPrepSquashErrors:
    """Tests for squash-related failures."""

    def test_squash_conflict(self, tmp_path: Path) -> None:
        """Test error when squash has merge conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_conflict()
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "squash_conflict"
        assert "Merge conflicts detected while squashing" in result.message

    def test_squash_failed(self, tmp_path: Path) -> None:
        """Test error when squash fails for non-conflict reason."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_failure(stderr="Something went wrong")
        )

        events, result = collect_events(execute_prep(ops, tmp_path, session_id="test-session"))

        assert isinstance(result, PrepError)
        assert result.success is False
        assert result.error_type == "squash_failed"
        assert "Failed to squash commits" in result.message
