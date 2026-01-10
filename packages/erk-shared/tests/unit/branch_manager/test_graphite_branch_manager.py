"""Unit tests for GraphiteBranchManager.

Tests the delete_branch() method with LBYL fallback to git when
Graphite can't handle the branch (untracked or diverged).
"""

from pathlib import Path

from erk_shared.branch_manager.graphite import GraphiteBranchManager
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit


def test_delete_branch_uses_graphite_when_tracked_and_not_diverged() -> None:
    """When branch is tracked and SHA matches, Graphite delete is used."""
    branch_sha = "abc123"
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": branch_sha},
    )
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=branch_sha,  # Same SHA - not diverged
            ),
        },
    )

    manager = GraphiteBranchManager(git=fake_git, graphite=fake_graphite)
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_delete_branch_falls_back_to_git_when_untracked() -> None:
    """When branch is not tracked by Graphite, git delete is used."""
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "abc123"},
    )
    fake_graphite = FakeGraphite(
        branches={},  # Branch not tracked
    )

    manager = GraphiteBranchManager(git=fake_git, graphite=fake_graphite)
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was NOT called
    assert fake_graphite.delete_branch_calls == []
    # Git delete WAS called with force=True
    assert fake_git.deleted_branches == ["feature-branch"]


def test_delete_branch_falls_back_to_git_when_diverged() -> None:
    """When branch SHA differs from Graphite's cached SHA, git delete is used."""
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "actual-sha-456"},
    )
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="cached-sha-123",  # Different SHA - diverged
            ),
        },
    )

    manager = GraphiteBranchManager(git=fake_git, graphite=fake_graphite)
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was NOT called
    assert fake_graphite.delete_branch_calls == []
    # Git delete WAS called with force=True
    assert fake_git.deleted_branches == ["feature-branch"]


def test_delete_branch_uses_graphite_when_commit_sha_is_none() -> None:
    """When Graphite has no cached SHA, Graphite delete is still used.

    This can happen for branches that were just tracked but haven't been
    synced yet. We still try Graphite since it's tracked.
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={"feature-branch": "abc123"},
    )
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=None,  # No cached SHA
            ),
        },
    )

    manager = GraphiteBranchManager(git=fake_git, graphite=fake_graphite)
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called (branch is tracked)
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []


def test_delete_branch_uses_graphite_when_git_branch_head_is_none() -> None:
    """When git can't find branch head, Graphite delete is still used.

    This might happen for edge cases where the branch exists but
    we can't determine its SHA. Since it's tracked, try Graphite.
    """
    repo_root = Path("/repo")

    fake_git = FakeGit(
        branch_heads={},  # No branch head known
    )
    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="cached-sha-123",
            ),
        },
    )

    manager = GraphiteBranchManager(git=fake_git, graphite=fake_graphite)
    manager.delete_branch(repo_root, "feature-branch")

    # Graphite delete was called (branch is tracked and can't compare SHAs)
    assert fake_graphite.delete_branch_calls == [(repo_root, "feature-branch")]
    # Git delete was NOT called
    assert fake_git.deleted_branches == []
