"""Unit tests for GraphiteBranchManager."""

from pathlib import Path

import pytest

from erk_shared.branch_manager.graphite import GraphiteBranchManager
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub

REPO_ROOT = Path("/fake/repo")


def test_create_branch_from_origin_when_local_matches_remote() -> None:
    """Test that create_branch works when local and remote are in sync."""
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "abc123",
            "origin/parent-branch": "abc123",  # In sync
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # When creating branch from origin/parent-branch
    manager.create_branch(REPO_ROOT, "new-feature", "origin/parent-branch")

    # The branch should be created and tracked without any delete/recreate
    assert any(branch == "new-feature" for (_, branch, _) in fake_git_branch_ops.created_branches)
    # No branches were deleted since local matches remote
    assert "parent-branch" not in fake_git_branch_ops.deleted_branches
    # Track was called with local branch name
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


def test_create_branch_from_origin_when_local_diverged() -> None:
    """Test that create_branch updates local branch when diverged from remote.

    This is the core bug fix: when local parent has diverged from origin/parent,
    the local branch needs to be updated to match origin before Graphite tracking.
    """
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "local123",  # Local is at different commit
            "origin/parent-branch": "remote456",  # Origin has been rebased/force-pushed
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # When creating branch from origin/parent-branch (diverged case)
    manager.create_branch(REPO_ROOT, "new-feature", "origin/parent-branch")

    # The diverged local branch should be deleted and recreated
    assert "parent-branch" in fake_git_branch_ops.deleted_branches
    # Should be recreated from the remote ref
    created_branches = [
        (branch, start) for (_, branch, start) in fake_git_branch_ops.created_branches
    ]
    assert ("parent-branch", "origin/parent-branch") in created_branches

    # The new branch should be created and tracked
    assert ("new-feature", "origin/parent-branch") in created_branches
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


def test_create_branch_from_origin_when_local_missing() -> None:
    """Test that create_branch creates local branch when it doesn't exist."""
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main"]},  # parent-branch doesn't exist locally
        branch_heads={
            "origin/parent-branch": "remote456",
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # When creating branch from origin/parent-branch (local missing)
    manager.create_branch(REPO_ROOT, "new-feature", "origin/parent-branch")

    # The local branch should be created from remote
    created_branches = [
        (branch, start) for (_, branch, start) in fake_git_branch_ops.created_branches
    ]
    assert ("parent-branch", "origin/parent-branch") in created_branches

    # No deletion since branch didn't exist
    assert "parent-branch" not in fake_git_branch_ops.deleted_branches

    # Track was called with local branch name
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


def test_create_branch_from_origin_when_local_checked_out_raises() -> None:
    """Test that create_branch raises when diverged branch is checked out."""
    worktree_path = Path("/fake/worktree")
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main", worktree_path: "parent-branch"},
        worktrees={
            REPO_ROOT: [
                WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="parent-branch"),
            ]
        },
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "local123",  # Diverged
            "origin/parent-branch": "remote456",
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # Should raise because the diverged branch is checked out in a worktree
    with pytest.raises(RuntimeError, match="Cannot update diverged branch"):
        manager.create_branch(REPO_ROOT, "new-feature", "origin/parent-branch")


def test_create_branch_from_local_branch_no_remote_sync() -> None:
    """Test that create_branch from local branch doesn't do remote sync."""
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "abc123",
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()
    fake_graphite = FakeGraphite()
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # When creating branch from local branch (not origin/...)
    manager.create_branch(REPO_ROOT, "new-feature", "parent-branch")

    # Should not delete or recreate parent-branch
    assert "parent-branch" not in fake_git_branch_ops.deleted_branches
    # Only the new-feature branch should be created
    created_branches = [branch for (_, branch, _) in fake_git_branch_ops.created_branches]
    assert "parent-branch" not in created_branches
    assert "new-feature" in created_branches
