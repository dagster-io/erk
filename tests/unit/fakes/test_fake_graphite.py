"""Tests for FakeGraphite test infrastructure.

These tests verify that FakeGraphite correctly simulates Graphite operations,
providing reliable test doubles for CLI tests.
"""

from pathlib import Path

import pytest

from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.gateway.graphite.branch_ops.fake import FakeGraphiteBranchOps
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata


def test_fake_graphite_ops_initialization() -> None:
    """Test that FakeGraphite initializes with empty state."""
    ops = FakeGraphite()
    git_ops = FakeGit()

    branches = ops.get_all_branches(git_ops, Path("/repo"))
    assert branches == {}

    prs = ops.get_prs_from_graphite(git_ops, Path("/repo"))
    assert prs == {}

    stack = ops.get_branch_stack(git_ops, Path("/repo"), "any-branch")
    assert stack is None


def test_fake_graphite_ops_get_all_branches() -> None:
    """Test that get_all_branches returns pre-configured BranchMetadata dict."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
        "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    result = ops.get_all_branches(git_ops, Path("/repo"))

    assert len(result) == 2
    assert result["main"].name == "main"
    assert result["main"].parent is None
    assert result["main"].children == ["feature-1"]
    assert result["feature-1"].parent == "main"


def test_fake_graphite_ops_get_branch_stack() -> None:
    """Test that get_branch_stack returns pre-configured stacks."""
    stacks = {
        "feature-1": ["main", "feature-1", "feature-2"],
    }
    ops = FakeGraphite(stacks=stacks)
    git_ops = FakeGit()

    result = ops.get_branch_stack(git_ops, Path("/repo"), "feature-1")

    assert result == ["main", "feature-1", "feature-2"]


def test_fake_graphite_ops_get_branch_stack_unknown() -> None:
    """Test that get_branch_stack returns None for unknown branch."""
    stacks = {
        "feature-1": ["main", "feature-1"],
    }
    ops = FakeGraphite(stacks=stacks)
    git_ops = FakeGit()

    result = ops.get_branch_stack(git_ops, Path("/repo"), "nonexistent")

    assert result is None


def test_fake_graphite_ops_get_parent_branch() -> None:
    """Test that parent relationships work from branches metadata."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature"], commit_sha="abc123"),
        "feature": BranchMetadata.branch("feature", "main", commit_sha="def456"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    result = ops.get_all_branches(git_ops, Path("/repo"))

    assert result["feature"].parent == "main"
    assert result["main"].parent is None


def test_fake_graphite_ops_get_child_branches() -> None:
    """Test that child relationships work from branches metadata."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feat-1", "feat-2"], commit_sha="abc123"),
        "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
        "feat-2": BranchMetadata.branch("feat-2", "main", commit_sha="ghi789"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    result = ops.get_all_branches(git_ops, Path("/repo"))

    assert result["main"].children == ["feat-1", "feat-2"]
    assert result["feat-1"].children == []


def test_fake_graphite_ops_branch_hierarchy() -> None:
    """Test parent→child relationships in multi-level hierarchy."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["level-1"], commit_sha="abc123"),
        "level-1": BranchMetadata.branch(
            "level-1", "main", children=["level-2"], commit_sha="def456"
        ),
        "level-2": BranchMetadata.branch("level-2", "level-1", commit_sha="ghi789"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    result = ops.get_all_branches(git_ops, Path("/repo"))

    # Verify parent chain
    assert result["level-2"].parent == "level-1"
    assert result["level-1"].parent == "main"
    assert result["main"].parent is None

    # Verify child chain
    assert result["main"].children == ["level-1"]
    assert result["level-1"].children == ["level-2"]
    assert result["level-2"].children == []


def test_fake_graphite_ops_stack_traversal() -> None:
    """Test that get_branch_stack builds stack from branch metadata."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
        "feature-1": BranchMetadata.branch(
            "feature-1", "main", children=["feature-2"], commit_sha="def456"
        ),
        "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # Get stack for middle branch - should include upstack and downstack
    result = ops.get_branch_stack(git_ops, Path("/repo"), "feature-1")

    assert result == ["main", "feature-1", "feature-2"]


def test_fake_graphite_ops_sync_noop() -> None:
    """Test that sync exists and doesn't crash."""
    ops = FakeGraphite()

    # Should not raise
    ops.sync(Path("/repo"), force=False, quiet=True)


def test_fake_graphite_ops_sync_tracks_calls() -> None:
    """Test that sync tracks calls via sync_calls property."""
    ops = FakeGraphite()

    ops.sync(Path("/repo1"), force=True, quiet=False)
    ops.sync(Path("/repo2"), force=False, quiet=True)

    assert len(ops.sync_calls) == 2
    assert ops.sync_calls[0] == (Path("/repo1"), True, False)
    assert ops.sync_calls[1] == (Path("/repo2"), False, True)


def test_fake_graphite_ops_sync_raises() -> None:
    """Test that sync can be configured to raise exceptions."""
    test_error = RuntimeError("Sync failed")
    ops = FakeGraphite(sync_raises=test_error)

    with pytest.raises(RuntimeError, match="Sync failed"):
        ops.sync(Path("/repo"), force=False, quiet=True)


def test_fake_graphite_ops_get_prs_from_graphite() -> None:
    """Test that get_prs_from_graphite returns pre-configured data."""
    pr_info = {
        "feature": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="owner",
            repo="repo",
        ),
    }
    ops = FakeGraphite(pr_info=pr_info)
    git_ops = FakeGit()

    result = ops.get_prs_from_graphite(git_ops, Path("/repo"))

    assert len(result) == 1
    assert result["feature"].number == 123
    assert result["feature"].state == "OPEN"


def test_fake_graphite_ops_get_graphite_url() -> None:
    """Test that get_graphite_url constructs correct URL."""
    ops = FakeGraphite()

    url = ops.get_graphite_url(GitHubRepoId("testowner", "testrepo"), 456)

    assert url == "https://app.graphite.com/github/pr/testowner/testrepo/456"


def test_fake_graphite_ops_branches_only_config() -> None:
    """Test configuration with only branches (no stacks)."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature"], commit_sha="abc123"),
        "feature": BranchMetadata.branch("feature", "main", commit_sha="def456"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # Should build stack from branch metadata
    result = ops.get_branch_stack(git_ops, Path("/repo"), "feature")

    assert result == ["main", "feature"]


def test_fake_graphite_ops_stacks_only_config() -> None:
    """Test configuration with only stacks (no branches)."""
    stacks = {
        "feature": ["main", "feature"],
    }
    ops = FakeGraphite(stacks=stacks)
    git_ops = FakeGit()

    result = ops.get_branch_stack(git_ops, Path("/repo"), "feature")

    assert result == ["main", "feature"]

    # get_all_branches should return empty
    branches = ops.get_all_branches(git_ops, Path("/repo"))
    assert branches == {}


def test_fake_graphite_ops_combined_config() -> None:
    """Test that stacks take precedence over branches when both configured."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feat-a"], commit_sha="abc123"),
        "feat-a": BranchMetadata.branch("feat-a", "main", commit_sha="def456"),
    }
    stacks = {
        "feat-b": ["main", "feat-b", "feat-c"],
    }
    ops = FakeGraphite(branches=branches, stacks=stacks)
    git_ops = FakeGit()

    # Stacks should take precedence
    result = ops.get_branch_stack(git_ops, Path("/repo"), "feat-b")
    assert result == ["main", "feat-b", "feat-c"]

    # But branches should still be available
    branches_result = ops.get_all_branches(git_ops, Path("/repo"))
    assert "feat-a" in branches_result


def test_fake_graphite_ops_missing_lookups() -> None:
    """Test behavior when looking up unknown branch/stack."""
    ops = FakeGraphite()
    git_ops = FakeGit()

    # Unknown branch with no configuration
    result = ops.get_branch_stack(git_ops, Path("/repo"), "unknown")
    assert result is None

    # get_all_branches with no configuration
    branches = ops.get_all_branches(git_ops, Path("/repo"))
    assert branches == {}


def test_fake_graphite_ops_stack_returns_copy() -> None:
    """Test that get_branch_stack returns a copy (not original list)."""
    original_stack = ["main", "feature"]
    stacks = {"feature": original_stack}
    ops = FakeGraphite(stacks=stacks)
    git_ops = FakeGit()

    result = ops.get_branch_stack(git_ops, Path("/repo"), "feature")

    # Modify result
    if result is not None:
        result.append("modified")

    # Original should be unchanged
    assert original_stack == ["main", "feature"]


def test_fake_graphite_is_branch_tracked_returns_true_for_tracked() -> None:
    """Test that is_branch_tracked returns True for branches in branches dict."""
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature"]),
        "feature": BranchMetadata.branch("feature", "main"),
    }
    ops = FakeGraphite(branches=branches)

    assert ops.is_branch_tracked(Path("/repo"), "main") is True
    assert ops.is_branch_tracked(Path("/repo"), "feature") is True


def test_fake_graphite_is_branch_tracked_returns_false_for_untracked() -> None:
    """Test that is_branch_tracked returns False for branches not in branches dict."""
    branches = {
        "main": BranchMetadata.trunk("main"),
    }
    ops = FakeGraphite(branches=branches)

    # "untracked-branch" is not in branches dict
    assert ops.is_branch_tracked(Path("/repo"), "untracked-branch") is False
    assert ops.is_branch_tracked(Path("/repo"), "nonexistent") is False


def test_fake_graphite_is_branch_tracked_empty_branches() -> None:
    """Test that is_branch_tracked returns False when no branches configured."""
    ops = FakeGraphite()

    assert ops.is_branch_tracked(Path("/repo"), "any-branch") is False


def test_fake_graphite_is_branch_diverged_from_tracking_no_divergence() -> None:
    """Test that is_branch_diverged_from_tracking returns False when SHAs match."""
    branches = {
        "main": BranchMetadata.trunk("main", commit_sha="abc123", tracked_revision="abc123"),
        "feature": BranchMetadata.branch(
            "feature", "main", commit_sha="def456", tracked_revision="def456"
        ),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # Both branches have matching SHAs - not diverged
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "main") is False
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "feature") is False


def test_fake_graphite_is_branch_diverged_from_tracking_with_divergence() -> None:
    """Test that is_branch_diverged_from_tracking returns True when SHAs differ."""
    branches = {
        "main": BranchMetadata.trunk("main", commit_sha="abc123", tracked_revision="abc123"),
        "feature": BranchMetadata.branch(
            "feature",
            "main",
            commit_sha="new456",  # Actual git SHA (after rebase)
            tracked_revision="old456",  # Stale Graphite cache
        ),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # main has matching SHAs - not diverged
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "main") is False

    # feature has mismatched SHAs - diverged
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "feature") is True


def test_fake_graphite_is_branch_diverged_from_tracking_untracked_branch() -> None:
    """Test that is_branch_diverged_from_tracking returns False for untracked branch."""
    branches = {
        "main": BranchMetadata.trunk("main", commit_sha="abc123"),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # "untracked" is not in branches - not diverged (returns False)
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "untracked") is False


def test_fake_graphite_is_branch_diverged_from_tracking_missing_tracked_revision() -> None:
    """Test that is_branch_diverged_from_tracking returns False when tracked_revision is None."""
    branches = {
        "main": BranchMetadata(
            name="main",
            parent=None,
            children=[],
            is_trunk=True,
            commit_sha="abc123",
            tracked_revision=None,  # No tracked revision
        ),
    }
    ops = FakeGraphite(branches=branches)
    git_ops = FakeGit()

    # Missing tracked_revision - assume not diverged
    assert ops.is_branch_diverged_from_tracking(git_ops, Path("/repo"), "main") is False


def test_fake_graphite_branch_ops_retrack_branch_tracks_calls() -> None:
    """Test that retrack_branch tracks calls via retrack_branch_calls property."""
    ops = FakeGraphite()
    branch_ops = ops.create_linked_branch_ops()

    branch_ops.retrack_branch(Path("/repo"), "feature-1")
    branch_ops.retrack_branch(Path("/repo2"), "feature-2")

    assert len(branch_ops.retrack_branch_calls) == 2
    assert branch_ops.retrack_branch_calls[0] == (Path("/repo"), "feature-1")
    assert branch_ops.retrack_branch_calls[1] == (Path("/repo2"), "feature-2")


def test_fake_graphite_branch_ops_retrack_branch_raises() -> None:
    """Test that retrack_branch can be configured to raise exceptions."""
    test_error = RuntimeError("Retrack failed")
    branch_ops = FakeGraphiteBranchOps(retrack_branch_raises=test_error)

    with pytest.raises(RuntimeError, match="Retrack failed"):
        branch_ops.retrack_branch(Path("/repo"), "feature")
