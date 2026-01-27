"""Unit tests for FakeBranchManager."""

from pathlib import Path

from erk_shared.gateway.branch_manager.fake import FakeBranchManager
from erk_shared.gateway.branch_manager.types import PrInfo


def test_delete_branch_tracks_deletion() -> None:
    """Test that delete_branch records branch in deleted_branches list."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    manager.delete_branch(repo_root, "feature-branch")

    assert manager.deleted_branches == [("feature-branch", False)]


def test_delete_branch_tracks_multiple_deletions() -> None:
    """Test that multiple delete_branch calls are all tracked."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    manager.delete_branch(repo_root, "branch-1")
    manager.delete_branch(repo_root, "branch-2")
    manager.delete_branch(repo_root, "branch-3")

    assert manager.deleted_branches == [
        ("branch-1", False),
        ("branch-2", False),
        ("branch-3", False),
    ]


def test_deleted_branches_returns_copy() -> None:
    """Test that deleted_branches property returns a copy, not the internal list."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    manager.delete_branch(repo_root, "feature-branch")
    branches = manager.deleted_branches

    # Modify the returned list
    branches.append(("should-not-appear", False))

    # Verify internal state wasn't modified
    assert manager.deleted_branches == [("feature-branch", False)]


def test_delete_branch_tracks_force_flag() -> None:
    """Test that delete_branch records the force flag for assertions."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    manager.delete_branch(repo_root, "soft-delete")
    manager.delete_branch(repo_root, "force-delete", force=True)

    assert manager.deleted_branches == [
        ("soft-delete", False),
        ("force-delete", True),
    ]


def test_create_branch_tracks_creation() -> None:
    """Test that create_branch records branch in created_branches list."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    manager.create_branch(repo_root, "new-feature", "main")

    assert manager.created_branches == [("new-feature", "main")]


def test_get_pr_for_branch_returns_configured_pr() -> None:
    """Test that get_pr_for_branch returns pre-configured PR info."""
    pr_info = PrInfo(number=123, state="OPEN", is_draft=False, from_fallback=False)
    manager = FakeBranchManager(pr_info={"feature-branch": pr_info})
    repo_root = Path("/fake/repo")

    result = manager.get_pr_for_branch(repo_root, "feature-branch")

    assert result == pr_info


def test_get_pr_for_branch_returns_none_for_unknown_branch() -> None:
    """Test that get_pr_for_branch returns None for unconfigured branches."""
    manager = FakeBranchManager()
    repo_root = Path("/fake/repo")

    result = manager.get_pr_for_branch(repo_root, "unknown-branch")

    assert result is None


def test_is_graphite_managed_returns_configured_value() -> None:
    """Test that is_graphite_managed returns the configured graphite_mode."""
    manager_default = FakeBranchManager()
    manager_graphite = FakeBranchManager(graphite_mode=True)

    assert manager_default.is_graphite_managed() is False
    assert manager_graphite.is_graphite_managed() is True
