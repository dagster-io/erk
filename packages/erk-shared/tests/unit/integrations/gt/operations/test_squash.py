"""Tests for execute_squash operation.

Tests verify idempotent squash behavior: squashes only when needed,
skips when already single commit, and handles errors appropriately.
"""

from pathlib import Path

from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.kit_cli_commands.gt.idempotent_squash import (
    SquashError,
    SquashSuccess,
    execute_squash,
)


def test_execute_squash_no_commits(tmp_path: Path) -> None:
    """Test squash fails when no commits exist ahead of trunk."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(0)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashError)
    assert result.success is False
    assert result.error == "no_commits"
    assert "No commits found ahead of main" in result.message


def test_execute_squash_single_commit_already(tmp_path: Path) -> None:
    """Test squash returns success with no-op when already single commit."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashSuccess)
    assert result.success is True
    assert result.action == "already_single_commit"
    assert result.commit_count == 1
    assert "Already a single commit, no squash needed" in result.message


def test_execute_squash_multiple_commits_success(tmp_path: Path) -> None:
    """Test squash succeeds when multiple commits exist."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(3)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashSuccess)
    assert result.success is True
    assert result.action == "squashed"
    assert result.commit_count == 3
    assert "Squashed 3 commits into 1" in result.message


def test_execute_squash_conflict(tmp_path: Path) -> None:
    """Test squash fails when merge conflicts occur."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(2)
        .with_squash_conflict()
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashError)
    assert result.success is False
    assert result.error == "squash_conflict"
    assert "Merge conflicts detected during squash" in result.message


def test_execute_squash_generic_failure(tmp_path: Path) -> None:
    """Test squash fails with generic error when squash operation fails."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(2)
        .with_squash_failure(stderr="Unknown error occurred")
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashError)
    assert result.success is False
    assert result.error == "squash_failed"
    assert "Failed to squash" in result.message


def test_execute_squash_with_master_trunk(tmp_path: Path) -> None:
    """Test squash works with master trunk instead of main."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_trunk_branch("master")
        .with_branch("feature", parent="master")
        .with_commits(2)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashSuccess)
    assert result.success is True
    assert result.action == "squashed"
    assert result.commit_count == 2


def test_execute_squash_boundary_two_commits(tmp_path: Path) -> None:
    """Test squash with exactly 2 commits (minimum for squash to trigger)."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(2)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashSuccess)
    assert result.success is True
    assert result.action == "squashed"
    assert result.commit_count == 2
    assert "Squashed 2 commits into 1" in result.message


def test_execute_squash_many_commits(tmp_path: Path) -> None:
    """Test squash with many commits."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(10)
    )

    # Act
    result = execute_squash(ops=ops)

    # Assert
    assert isinstance(result, SquashSuccess)
    assert result.success is True
    assert result.action == "squashed"
    assert result.commit_count == 10
    assert "Squashed 10 commits into 1" in result.message
