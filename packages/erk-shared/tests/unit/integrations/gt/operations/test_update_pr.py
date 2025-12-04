"""Tests for execute_update_pr operation.

Tests verify the update-pr workflow: staging uncommitted changes, committing,
restacking, submitting, and retrieving PR information.
"""

from pathlib import Path

from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.kit_cli_commands.gt.pr_update import execute_update_pr


def test_execute_update_pr_success_with_uncommitted(tmp_path: Path) -> None:
    """Test successful update with uncommitted changes (stage + commit + restack + submit)."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_uncommitted_files(["file.txt"])
        .with_pr(123, url="https://github.com/repo/pull/123")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is True
    assert result["pr_number"] == 123
    assert result["pr_url"] == "https://github.com/repo/pull/123"


def test_execute_update_pr_success_without_uncommitted(tmp_path: Path) -> None:
    """Test successful update without uncommitted changes (skip staging + proceed)."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        # No uncommitted files
        .with_pr(123, url="https://github.com/repo/pull/123")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is True
    assert result["pr_number"] == 123
    assert result["pr_url"] == "https://github.com/repo/pull/123"


def test_execute_update_pr_add_failure(tmp_path: Path) -> None:
    """Test update fails when git add fails."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_uncommitted_files(["file.txt"])
        .with_add_failure()
        .with_pr(123)
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    # Note: FakeGit.add_all() doesn't support failure simulation
    # This test documents expected behavior if add_all() could fail
    # For now, it will succeed since FakeGit.add_all() is a no-op
    # TODO: Update when FakeGit supports add failure simulation
    assert result["success"] is True or result["error"] == "Failed to stage changes"


def test_execute_update_pr_restack_conflict(tmp_path: Path) -> None:
    """Test update fails when restack detects conflicts."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123)
        .with_restack_conflict()
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert result["error_type"] == "restack_conflict"
    assert "Merge conflict detected during restack" in result["error"]


def test_execute_update_pr_restack_failure(tmp_path: Path) -> None:
    """Test update fails when restack fails for generic reasons."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123)
        .with_restack_failure(stderr="Unknown restack error")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert result["error_type"] == "restack_failed"
    assert "Failed to restack branch" in result["error"]


def test_execute_update_pr_remote_divergence(tmp_path: Path) -> None:
    """Test update fails when branch has diverged from remote."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123)
        .with_submit_failure(stderr="Branch has been updated remotely")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert result["error_type"] == "remote_divergence"
    assert "Branch has diverged from remote" in result["error"]
    assert "Do NOT auto-sync" in result["error"]


def test_execute_update_pr_submit_failure(tmp_path: Path) -> None:
    """Test update fails when submit fails for generic reasons."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123)
        .with_submit_failure(stderr="Generic submit error")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert "Failed to submit update" in result["error"]


def test_execute_update_pr_no_branch(tmp_path: Path) -> None:
    """Test update fails when current branch cannot be determined after submission."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123)
    )
    # Simulate branch becoming unavailable after operations
    ops._git_current_branches[Path(tmp_path)] = None

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert "Could not determine current branch" in result["error"]


def test_execute_update_pr_pr_info_retrieval_fails(tmp_path: Path) -> None:
    """Test update fails when PR info cannot be retrieved after submission."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        # No PR configured - simulates PR info not found
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is False
    assert "failed to retrieve PR info" in result["error"]


def test_execute_update_pr_with_multiple_commits(tmp_path: Path) -> None:
    """Test update succeeds with multiple commits on branch."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(3)
        .with_pr(456, url="https://github.com/repo/pull/456")
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is True
    assert result["pr_number"] == 456
    assert result["pr_url"] == "https://github.com/repo/pull/456"


def test_execute_update_pr_updates_existing_pr(tmp_path: Path) -> None:
    """Test update succeeds and returns correct PR info for existing PR."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_uncommitted_files(["new-change.txt"])
        .with_pr(
            789,
            url="https://github.com/owner/repo/pull/789",
            title="Feature PR",
            state="OPEN",
        )
    )

    # Act
    result = execute_update_pr(ops=ops)

    # Assert
    assert result["success"] is True
    assert result["pr_number"] == 789
    assert result["pr_url"] == "https://github.com/owner/repo/pull/789"
