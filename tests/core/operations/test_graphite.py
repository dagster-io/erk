"""Tests for Graphite helper methods."""

from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from tests.test_utils.paths import sentinel_path


def test_fake_graphite_ops_initialization() -> None:
    """Test that FakeGraphite can be initialized."""
    ops = FakeGraphite()
    assert ops is not None


def test_fake_graphite_ops_no_op() -> None:
    """Test that FakeGraphite operations are no-ops."""
    ops = FakeGraphite()
    # FakeGraphite is a simple stub - just verify it exists
    assert hasattr(ops, "__class__")
    assert ops.__class__.__name__ == "FakeGraphite"


def test_get_parent_branch_returns_parent() -> None:
    """Test get_parent_branch() returns correct parent from branches metadata."""
    # Arrange: Create branch hierarchy
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
        "feature-1": BranchMetadata.branch(
            "feature-1", "main", children=["feature-2"], commit_sha="def456"
        ),
        "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
    }
    graphite_ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()  # Not actually used by helper methods
    repo_root = sentinel_path()

    # Act & Assert: Test parent relationships
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "feature-2") == "feature-1"
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "feature-1") == "main"
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "main") is None


def test_get_parent_branch_returns_none_for_unknown_branch() -> None:
    """Test get_parent_branch() returns None if branch not tracked by graphite."""
    # Arrange
    branches = {
        "main": BranchMetadata.trunk("main", commit_sha="abc123"),
    }
    graphite_ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "unknown-branch") is None


def test_get_parent_branch_returns_none_when_no_branches() -> None:
    """Test get_parent_branch() returns None when no Graphite data available."""
    # Arrange: No branches configured
    graphite_ops = FakeGraphite()
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "any-branch") is None


def test_get_child_branches_returns_children() -> None:
    """Test get_child_branches() returns correct children from branches metadata."""
    # Arrange: Create branch hierarchy with multiple children
    branches = {
        "main": BranchMetadata.trunk(
            "main", children=["feature-1", "feature-2"], commit_sha="abc123"
        ),
        "feature-1": BranchMetadata.branch(
            "feature-1", "main", children=["feature-1-1"], commit_sha="def456"
        ),
        "feature-2": BranchMetadata.branch("feature-2", "main", commit_sha="ghi789"),
        "feature-1-1": BranchMetadata.branch("feature-1-1", "feature-1", commit_sha="jkl012"),
    }
    graphite_ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert: Test child relationships
    assert graphite_ops.get_child_branches(git_ops, repo_root, "main") == ["feature-1", "feature-2"]
    assert graphite_ops.get_child_branches(git_ops, repo_root, "feature-1") == ["feature-1-1"]
    assert graphite_ops.get_child_branches(git_ops, repo_root, "feature-2") == []
    assert graphite_ops.get_child_branches(git_ops, repo_root, "feature-1-1") == []


def test_get_child_branches_returns_empty_for_unknown_branch() -> None:
    """Test get_child_branches() returns empty list if branch not tracked."""
    # Arrange
    branches = {
        "main": BranchMetadata.trunk("main", commit_sha="abc123"),
    }
    graphite_ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert
    assert graphite_ops.get_child_branches(git_ops, repo_root, "unknown-branch") == []


def test_get_child_branches_returns_empty_when_no_branches() -> None:
    """Test get_child_branches() returns empty list when no Graphite data."""
    # Arrange: No branches configured
    graphite_ops = FakeGraphite()
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert
    assert graphite_ops.get_child_branches(git_ops, repo_root, "any-branch") == []


def test_helper_methods_work_with_stacks_configuration() -> None:
    """Test that helper methods work when FakeGraphite uses stacks parameter.

    Note: stacks parameter doesn't provide parent/child relationships, so helpers
    that rely on get_all_branches() should return empty/None with stacks-only config.
    """
    # Arrange: Use stacks parameter (simpler configuration)
    graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})
    git_ops = FakeGit()
    repo_root = sentinel_path()

    # Act & Assert: stacks doesn't populate get_all_branches(), so helpers return empty
    assert graphite_ops.get_parent_branch(git_ops, repo_root, "feature-2") is None
    assert graphite_ops.get_child_branches(git_ops, repo_root, "main") == []

    # But get_branch_stack() works with stacks
    expected_stack = ["main", "feature-1", "feature-2"]
    assert graphite_ops.get_branch_stack(git_ops, repo_root, "feature-1") == expected_stack
