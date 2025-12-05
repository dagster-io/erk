"""Tests for FakeGitRemotes (Layer 1: Fake infrastructure tests).

Verifies that the in-memory fake implementation behaves correctly:
- State management for remote branches and URLs
- Mutation tracking for test assertions
- Read operations return configured state
- Write operations record mutations
"""

from pathlib import Path

import pytest
from erk_shared.git.remotes import FakeGitRemotes


def test_branch_exists_on_remote_returns_false_when_not_configured() -> None:
    """Test that branch_exists_on_remote returns False for unconfigured branches."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    result = fake.branch_exists_on_remote(repo_root, "origin", "main")

    assert result is False


def test_branch_exists_on_remote_returns_true_when_configured() -> None:
    """Test that branch_exists_on_remote returns True for configured branches."""
    repo_root = Path("/repo")
    fake = FakeGitRemotes(
        remote_branches={
            repo_root: {
                "origin": ["main", "develop"],
            }
        }
    )

    result = fake.branch_exists_on_remote(repo_root, "origin", "main")

    assert result is True


def test_branch_exists_on_remote_checks_correct_remote() -> None:
    """Test that branch_exists_on_remote distinguishes between remotes."""
    repo_root = Path("/repo")
    fake = FakeGitRemotes(
        remote_branches={
            repo_root: {
                "origin": ["main"],
                "upstream": ["develop"],
            }
        }
    )

    # main exists on origin but not upstream
    assert fake.branch_exists_on_remote(repo_root, "origin", "main") is True
    assert fake.branch_exists_on_remote(repo_root, "upstream", "main") is False

    # develop exists on upstream but not origin
    assert fake.branch_exists_on_remote(repo_root, "upstream", "develop") is True
    assert fake.branch_exists_on_remote(repo_root, "origin", "develop") is False


def test_get_remote_url_returns_configured_url() -> None:
    """Test that get_remote_url returns the configured URL."""
    repo_root = Path("/repo")
    fake = FakeGitRemotes(
        remote_urls={
            repo_root: {
                "origin": "https://github.com/owner/repo.git",
            }
        }
    )

    url = fake.get_remote_url(repo_root, "origin")

    assert url == "https://github.com/owner/repo.git"


def test_get_remote_url_raises_when_remote_not_found() -> None:
    """Test that get_remote_url raises ValueError for missing remote."""
    repo_root = Path("/repo")
    fake = FakeGitRemotes(remote_urls={repo_root: {}})

    with pytest.raises(ValueError, match="Remote 'origin' not found"):
        fake.get_remote_url(repo_root, "origin")


def test_fetch_branch_tracks_mutation() -> None:
    """Test that fetch_branch records the operation for assertions."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    fake.fetch_branch(repo_root, "origin", "main")

    assert fake.fetched_branches == [("origin", "main")]


def test_pull_branch_tracks_mutation() -> None:
    """Test that pull_branch records the operation with ff_only flag."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    fake.pull_branch(repo_root, "origin", "main", ff_only=True)

    assert fake.pulled_branches == [("origin", "main", True)]


def test_push_to_remote_tracks_mutation() -> None:
    """Test that push_to_remote records the operation with set_upstream flag."""
    fake = FakeGitRemotes()
    cwd = Path("/repo")

    fake.push_to_remote(cwd, "origin", "feature", set_upstream=True)

    assert fake.pushed_branches == [("origin", "feature", True)]


def test_fetch_pr_ref_tracks_mutation() -> None:
    """Test that fetch_pr_ref records the operation."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    fake.fetch_pr_ref(repo_root, "origin", 123, "pr-123")

    assert fake.fetched_pr_refs == [("origin", 123, "pr-123")]


def test_multiple_operations_tracked_in_order() -> None:
    """Test that multiple operations are tracked in chronological order."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    fake.fetch_branch(repo_root, "origin", "main")
    fake.fetch_branch(repo_root, "origin", "develop")
    fake.push_to_remote(repo_root, "origin", "feature", set_upstream=False)

    assert fake.fetched_branches == [("origin", "main"), ("origin", "develop")]
    assert fake.pushed_branches == [("origin", "feature", False)]


def test_mutation_properties_return_copies() -> None:
    """Test that mutation tracking properties return copies, not internal state."""
    fake = FakeGitRemotes()
    repo_root = Path("/repo")

    fake.fetch_branch(repo_root, "origin", "main")
    first_result = fake.fetched_branches
    second_result = fake.fetched_branches

    # Properties return equal but distinct lists
    assert first_result == second_result
    assert first_result is not second_result
