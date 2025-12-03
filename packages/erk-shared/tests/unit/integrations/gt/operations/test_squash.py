"""Tests for execute_squash operation with event assertions.

Tests the idempotent squash logic which squashes commits only when there
are 2 or more commits. Single commit branches return success without modification.
"""

from pathlib import Path

from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.operations.squash import execute_squash
from erk_shared.integrations.gt.types import SquashError, SquashSuccess

from tests.unit.integrations.gt.operations.conftest import (
    collect_events,
    has_event_containing,
)


class TestSquashSuccess:
    """Tests for successful squash execution."""

    def test_single_commit_returns_success_no_op(self, tmp_path: Path) -> None:
        """Test single commit returns success without squashing."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashSuccess)
        assert result.success is True
        assert result.action == "already_single_commit"
        assert result.commit_count == 1
        assert "Already a single commit, no squash needed" in result.message

        # Should have the "already single commit" event
        assert has_event_containing(events, "Already a single commit")

    def test_multiple_commits_squashes_successfully(self, tmp_path: Path) -> None:
        """Test multiple commits get squashed."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashSuccess)
        assert result.success is True
        assert result.action == "squashed"
        assert result.commit_count == 3
        assert "Squashed 3 commits into 1" in result.message

        # Should have squash progress events
        assert has_event_containing(events, "Squashing 3 commits")
        assert has_event_containing(events, "Squashed 3 commits into 1")

    def test_two_commits_squashes(self, tmp_path: Path) -> None:
        """Test that exactly 2 commits triggers squash."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(2)
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashSuccess)
        assert result.success is True
        assert result.action == "squashed"
        assert result.commit_count == 2
        assert "Squashed 2 commits into 1" in result.message


class TestSquashErrors:
    """Tests for squash error scenarios."""

    def test_no_commits_returns_error(self, tmp_path: Path) -> None:
        """Test error when no commits found ahead of trunk."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(0)
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashError)
        assert result.success is False
        assert result.error == "no_commits"
        assert "No commits found ahead of" in result.message

        # Should have counting event before the error
        assert has_event_containing(events, "Counting commits")

    def test_squash_conflict_returns_error(self, tmp_path: Path) -> None:
        """Test error when squash has merge conflicts."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_conflict()
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashError)
        assert result.success is False
        assert result.error == "squash_conflict"
        assert "Merge conflicts detected during squash" in result.message

    def test_squash_failure_returns_error(self, tmp_path: Path) -> None:
        """Test error when squash fails for non-conflict reason."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_failure(stderr="Something went wrong")
        )

        events, result = collect_events(execute_squash(ops, tmp_path))

        assert isinstance(result, SquashError)
        assert result.success is False
        assert result.error == "squash_failed"
        assert "Failed to squash" in result.message
