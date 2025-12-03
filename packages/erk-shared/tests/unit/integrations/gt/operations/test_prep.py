"""Tests for execute_prep operation.

Tests verify both success paths and error handling for PR preparation,
including authentication checks, conflict detection, squashing, and diff extraction.
"""

from pathlib import Path

import pytest
from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.kit_cli_commands.gt.pr_prep import (
    PrepError,
    PrepResult,
    execute_prep,
)


def test_execute_prep_success_single_commit(tmp_path: Path) -> None:
    """Test successful prep with single commit (no squash needed)."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepResult)
    assert result.success is True
    assert result.current_branch == "feature"
    assert result.parent_branch == "main"
    assert result.commit_count == 1
    assert result.squashed is False
    assert "Single commit, no squash needed" in result.message
    assert Path(result.diff_file).exists()


def test_execute_prep_success_multiple_commits_squashed(tmp_path: Path) -> None:
    """Test successful prep with multiple commits (squashing required)."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(3)
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepResult)
    assert result.success is True
    assert result.current_branch == "feature"
    assert result.parent_branch == "main"
    assert result.commit_count == 3
    assert result.squashed is True
    assert "Squashed 3 commits into 1" in result.message
    assert Path(result.diff_file).exists()


def test_execute_prep_gt_not_authenticated(tmp_path: Path) -> None:
    """Test prep fails when Graphite is not authenticated."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_gt_unauthenticated()
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "gt_not_authenticated"
    assert "Graphite CLI (gt) is not authenticated" in result.message
    assert result.details["authenticated"] is False


def test_execute_prep_gh_not_authenticated(tmp_path: Path) -> None:
    """Test prep fails when GitHub is not authenticated."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_gh_unauthenticated()
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "gh_not_authenticated"
    assert "GitHub CLI (gh) is not authenticated" in result.message
    assert result.details["authenticated"] is False


def test_execute_prep_no_branch(tmp_path: Path) -> None:
    """Test prep fails when current branch cannot be determined."""
    # Arrange
    ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_no_branch()

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "no_branch"
    assert "Could not determine current branch" in result.message


def test_execute_prep_no_parent(tmp_path: Path) -> None:
    """Test prep fails when parent branch cannot be determined."""
    # Arrange
    ops = FakeGtKitOps().with_repo_root(str(tmp_path)).with_orphan_branch("orphan")

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "no_parent"
    assert "Could not determine parent branch" in result.message
    assert result.details["branch_name"] == "orphan"


def test_execute_prep_restack_conflict(tmp_path: Path) -> None:
    """Test prep fails when restack detects conflicts."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_restack_conflict()
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "restack_conflict"
    assert "Restack conflicts detected" in result.message
    assert result.details["branch_name"] == "feature"
    assert result.details["parent_branch"] == "main"


def test_execute_prep_no_commits(tmp_path: Path) -> None:
    """Test prep fails when branch has no commits ahead of parent."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(0)
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "no_commits"
    assert "No commits found in branch" in result.message
    assert result.details["branch_name"] == "feature"
    assert result.details["parent_branch"] == "main"


def test_execute_prep_squash_conflict(tmp_path: Path) -> None:
    """Test prep fails when squash detects conflicts."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(2)
        .with_squash_conflict()
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "squash_conflict"
    assert "Merge conflicts detected while squashing commits" in result.message
    assert result.details["branch_name"] == "feature"
    assert result.details["commit_count"] == "2"


def test_execute_prep_squash_failed(tmp_path: Path) -> None:
    """Test prep fails when squash fails for generic reasons."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(2)
        .with_squash_failure(stderr="Unknown error")
    )

    # Act
    result = execute_prep(session_id="test-session", ops=ops)

    # Assert
    assert isinstance(result, PrepError)
    assert result.success is False
    assert result.error_type == "squash_failed"
    assert "Failed to squash commits" in result.message
    assert result.details["branch_name"] == "feature"
    assert result.details["commit_count"] == "2"


def test_execute_prep_diff_file_written_to_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that diff file is written to scratch directory with correct naming."""
    # Arrange
    # Change cwd to tmp_path to ensure scratch dir is created there
    monkeypatch.chdir(tmp_path)

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
    )

    # Act
    result = execute_prep(session_id="test-session-123", ops=ops)

    # Assert
    assert isinstance(result, PrepResult)
    diff_path = Path(result.diff_file)
    assert diff_path.exists()
    assert diff_path.suffix == ".diff"
    assert "pr-prep-diff-" in diff_path.name
    # Verify it's in the scratch directory structure (.erk/scratch/<session-id>/)
    assert ".erk/scratch" in str(diff_path)
    assert "test-session-123" in str(diff_path)
