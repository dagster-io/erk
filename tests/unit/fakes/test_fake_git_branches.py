"""Tests for FakeGitBranches.

Layer 1 (Fake Infrastructure Tests): Verify that the fake implementation
behaves correctly and can be used reliably in other tests.
"""

from pathlib import Path

import pytest
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.branches.fake import FakeGitBranches


def test_get_current_branch_returns_configured_branch() -> None:
    """Test that get_current_branch returns the configured branch."""
    repo = Path("/repo")
    fake = FakeGitBranches(current_branches={repo: "main"})

    assert fake.get_current_branch(repo) == "main"


def test_get_current_branch_returns_none_for_unknown_path() -> None:
    """Test that get_current_branch returns None for paths without a branch."""
    fake = FakeGitBranches()

    assert fake.get_current_branch(Path("/unknown")) is None


def test_detect_trunk_branch_returns_configured_trunk() -> None:
    """Test that detect_trunk_branch returns the configured trunk."""
    repo = Path("/repo")
    fake = FakeGitBranches(trunk_branches={repo: "master"})

    assert fake.detect_trunk_branch(repo) == "master"


def test_detect_trunk_branch_defaults_to_main() -> None:
    """Test that detect_trunk_branch defaults to 'main' when not configured."""
    fake = FakeGitBranches()

    assert fake.detect_trunk_branch(Path("/repo")) == "main"


def test_validate_trunk_branch_succeeds_when_branch_exists() -> None:
    """Test that validate_trunk_branch returns the branch name when valid."""
    repo = Path("/repo")
    fake = FakeGitBranches(trunk_branches={repo: "main"})

    assert fake.validate_trunk_branch(repo, "main") == "main"


def test_validate_trunk_branch_checks_local_branches() -> None:
    """Test that validate_trunk_branch also checks local_branches."""
    repo = Path("/repo")
    fake = FakeGitBranches(local_branches={repo: ["main", "develop"]})

    assert fake.validate_trunk_branch(repo, "main") == "main"


def test_validate_trunk_branch_raises_when_branch_missing() -> None:
    """Test that validate_trunk_branch raises when branch doesn't exist."""
    repo = Path("/repo")
    fake = FakeGitBranches(trunk_branches={repo: "main"})

    with pytest.raises(RuntimeError, match="does not exist in repository"):
        fake.validate_trunk_branch(repo, "nonexistent")


def test_list_local_branches_returns_configured_branches() -> None:
    """Test that list_local_branches returns the configured branches."""
    repo = Path("/repo")
    branches = ["main", "develop", "feature"]
    fake = FakeGitBranches(local_branches={repo: branches})

    assert fake.list_local_branches(repo) == branches


def test_list_local_branches_returns_empty_for_unknown_repo() -> None:
    """Test that list_local_branches returns empty list for unknown repo."""
    fake = FakeGitBranches()

    assert fake.list_local_branches(Path("/unknown")) == []


def test_list_remote_branches_returns_configured_branches() -> None:
    """Test that list_remote_branches returns the configured branches."""
    repo = Path("/repo")
    branches = ["origin/main", "origin/develop"]
    fake = FakeGitBranches(remote_branches={repo: branches})

    assert fake.list_remote_branches(repo) == branches


def test_create_tracking_branch_tracks_mutation() -> None:
    """Test that create_tracking_branch tracks the mutation."""
    repo = Path("/repo")
    fake = FakeGitBranches()

    fake.create_tracking_branch(repo, "feature", "origin/feature")

    assert ("feature", "origin/feature") in fake.created_tracking_branches


def test_create_tracking_branch_adds_to_local_branches() -> None:
    """Test that create_tracking_branch adds branch to local branches."""
    repo = Path("/repo")
    fake = FakeGitBranches(local_branches={repo: ["main"]})

    fake.create_tracking_branch(repo, "feature", "origin/feature")

    assert "feature" in fake.list_local_branches(repo)


def test_create_tracking_branch_raises_configured_error() -> None:
    """Test that create_tracking_branch can raise configured errors."""
    import subprocess

    repo = Path("/repo")
    fake = FakeGitBranches(tracking_branch_failures={"feature": "Remote ref not found"})

    with pytest.raises(subprocess.CalledProcessError):
        fake.create_tracking_branch(repo, "feature", "origin/feature")


def test_delete_branch_tracks_mutation() -> None:
    """Test that delete_branch tracks the deletion."""
    repo = Path("/repo")
    fake = FakeGitBranches()

    fake.delete_branch(repo, "old-feature", force=False)

    assert "old-feature" in fake.deleted_branches


def test_delete_branch_with_graphite_tracks_mutation() -> None:
    """Test that delete_branch_with_graphite tracks the deletion."""
    repo = Path("/repo")
    fake = FakeGitBranches()

    fake.delete_branch_with_graphite(repo, "old-feature", force=True)

    assert "old-feature" in fake.deleted_branches


def test_delete_branch_raises_configured_error() -> None:
    """Test that delete_branch can raise configured errors."""
    import subprocess

    repo = Path("/repo")
    error = subprocess.CalledProcessError(1, ["git", "branch", "-d", "protected"])
    fake = FakeGitBranches(delete_branch_raises={"protected": error})

    with pytest.raises(RuntimeError, match="Failed to delete branch"):
        fake.delete_branch(repo, "protected", force=False)


def test_checkout_branch_tracks_mutation() -> None:
    """Test that checkout_branch tracks the checkout."""
    repo = Path("/repo")
    fake = FakeGitBranches()

    fake.checkout_branch(repo, "feature")

    assert (repo, "feature") in fake.checked_out_branches


def test_checkout_branch_updates_current_branch() -> None:
    """Test that checkout_branch updates the current branch."""
    repo = Path("/repo")
    fake = FakeGitBranches(current_branches={repo: "main"})

    fake.checkout_branch(repo, "feature")

    assert fake.get_current_branch(repo) == "feature"


def test_checkout_branch_validates_not_checked_out_elsewhere() -> None:
    """Test that checkout_branch validates branch isn't checked out in another worktree."""
    repo = Path("/repo")
    wt1 = Path("/repo")
    wt2 = Path("/repo/wt-feature")
    worktrees = [
        WorktreeInfo(path=wt1, branch="main", is_root=True),
        WorktreeInfo(path=wt2, branch="feature", is_root=False),
    ]
    fake = FakeGitBranches(worktrees={repo: worktrees})

    with pytest.raises(RuntimeError, match="already checked out at"):
        fake.checkout_branch(wt1, "feature")


def test_checkout_detached_tracks_mutation() -> None:
    """Test that checkout_detached tracks the detached checkout."""
    repo = Path("/repo")
    fake = FakeGitBranches()

    fake.checkout_detached(repo, "abc123")

    assert (repo, "abc123") in fake.detached_checkouts


def test_checkout_detached_sets_current_branch_to_none() -> None:
    """Test that checkout_detached sets current branch to None."""
    repo = Path("/repo")
    fake = FakeGitBranches(current_branches={repo: "main"})

    fake.checkout_detached(repo, "abc123")

    assert fake.get_current_branch(repo) is None


def test_get_branch_head_returns_configured_sha() -> None:
    """Test that get_branch_head returns the configured commit SHA."""
    repo = Path("/repo")
    fake = FakeGitBranches(branch_heads={"main": "abc123"})

    assert fake.get_branch_head(repo, "main") == "abc123"


def test_get_branch_head_returns_none_for_unknown_branch() -> None:
    """Test that get_branch_head returns None for unknown branches."""
    fake = FakeGitBranches()

    assert fake.get_branch_head(Path("/repo"), "unknown") is None


def test_mutation_tracking_properties_return_copies() -> None:
    """Test that mutation tracking properties return copies, not references."""
    fake = FakeGitBranches()
    fake.delete_branch(Path("/repo"), "test", force=False)

    deleted1 = fake.deleted_branches
    deleted2 = fake.deleted_branches

    assert deleted1 is not deleted2
    assert deleted1 == deleted2
