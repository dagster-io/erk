"""Tests for FakeIssueLinkBranches test infrastructure.

These tests verify that FakeIssueLinkBranches correctly simulates issue-linked
branch development operations, providing reliable test doubles for tests that
use the `gh issue develop` functionality.
"""

from tests.fakes.issue_link_branches import FakeIssueLinkBranches
from tests.test_utils.paths import sentinel_path


def test_fake_issue_link_branches_initialization() -> None:
    """Test that FakeIssueLinkBranches initializes with empty state."""
    dev = FakeIssueLinkBranches()

    # No existing branches
    assert dev.get_linked_branch(sentinel_path(), 123) is None

    # No created branches
    assert dev.created_branches == []


def test_fake_issue_link_branches_create_branch_new() -> None:
    """Test create_development_branch creates new branch when none exists."""
    dev = FakeIssueLinkBranches()

    result = dev.create_development_branch(sentinel_path(), 123)

    assert result.branch_name == "123-issue-branch"
    assert result.issue_number == 123
    assert result.already_existed is False


def test_fake_issue_link_branches_create_branch_existing() -> None:
    """Test create_development_branch returns existing branch when present."""
    dev = FakeIssueLinkBranches(existing_branches={123: "123-my-feature"})

    result = dev.create_development_branch(sentinel_path(), 123)

    assert result.branch_name == "123-my-feature"
    assert result.issue_number == 123
    assert result.already_existed is True


def test_fake_issue_link_branches_create_branch_tracks_mutation() -> None:
    """Test create_development_branch tracks created branches."""
    dev = FakeIssueLinkBranches()

    dev.create_development_branch(sentinel_path(), 100)
    dev.create_development_branch(sentinel_path(), 200)

    assert dev.created_branches == [
        (100, "100-issue-branch"),
        (200, "200-issue-branch"),
    ]


def test_fake_issue_link_branches_create_branch_no_tracking_for_existing() -> None:
    """Test create_development_branch doesn't track when branch already existed."""
    dev = FakeIssueLinkBranches(existing_branches={123: "123-existing"})

    dev.create_development_branch(sentinel_path(), 123)

    # Should not track because branch already existed
    assert dev.created_branches == []


def test_fake_issue_link_branches_create_branch_stores_for_get() -> None:
    """Test created branch is stored and retrievable via get_linked_branch."""
    dev = FakeIssueLinkBranches()

    dev.create_development_branch(sentinel_path(), 42)

    result = dev.get_linked_branch(sentinel_path(), 42)
    assert result == "42-issue-branch"


def test_fake_issue_link_branches_get_linked_branch_none() -> None:
    """Test get_linked_branch returns None when no branch exists."""
    dev = FakeIssueLinkBranches()

    result = dev.get_linked_branch(sentinel_path(), 999)

    assert result is None


def test_fake_issue_link_branches_get_linked_branch_existing() -> None:
    """Test get_linked_branch returns branch from existing_branches."""
    dev = FakeIssueLinkBranches(existing_branches={42: "42-feature-branch"})

    result = dev.get_linked_branch(sentinel_path(), 42)

    assert result == "42-feature-branch"


def test_fake_issue_link_branches_base_branch_ignored() -> None:
    """Test that base_branch parameter doesn't affect fake behavior."""
    dev = FakeIssueLinkBranches()

    result = dev.create_development_branch(sentinel_path(), 123, base_branch="develop")

    # Fake ignores base_branch since it doesn't actually create git branches
    assert result.branch_name == "123-issue-branch"
    assert result.already_existed is False


def test_fake_issue_link_branches_created_branches_read_only() -> None:
    """Test created_branches property returns a copy."""
    dev = FakeIssueLinkBranches()
    dev.create_development_branch(sentinel_path(), 1)

    branches = dev.created_branches
    branches.append((999, "should-not-persist"))

    # Modification to returned list shouldn't affect internal state
    assert dev.created_branches == [(1, "1-issue-branch")]


def test_fake_issue_link_branches_multiple_issues() -> None:
    """Test handling multiple issues independently."""
    dev = FakeIssueLinkBranches(existing_branches={10: "10-existing"})

    # Get existing
    result1 = dev.create_development_branch(sentinel_path(), 10)
    # Create new
    result2 = dev.create_development_branch(sentinel_path(), 20)
    # Get newly created
    result3 = dev.create_development_branch(sentinel_path(), 20)

    assert result1.already_existed is True
    assert result2.already_existed is False
    assert result3.already_existed is True

    # Only issue 20 was newly created
    assert dev.created_branches == [(20, "20-issue-branch")]

    # Both are now retrievable
    assert dev.get_linked_branch(sentinel_path(), 10) == "10-existing"
    assert dev.get_linked_branch(sentinel_path(), 20) == "20-issue-branch"
