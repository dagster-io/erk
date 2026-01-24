"""Unit tests for GraphiteBranchManager."""

from pathlib import Path

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
    # created_branches is now (cwd, branch_name, start_point, force)
    assert any(
        branch == "new-feature" for (_, branch, _, _) in fake_git_branch_ops.created_branches
    )
    # No branches were deleted since local matches remote
    assert "parent-branch" not in fake_git_branch_ops.deleted_branches
    # Track was called with local branch name
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


def test_create_branch_from_origin_when_local_diverged() -> None:
    """Test that create_branch auto-fixes diverged local branch.

    When the local parent has diverged from origin/parent, we force-update
    the local branch to match remote. This is safe because we've already
    checked out the new branch being created.
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

    # Should succeed - diverged local branch is force-updated to match remote
    manager.create_branch(REPO_ROOT, "new-feature", "origin/parent-branch")

    # new-feature should be created from origin/parent-branch
    # created_branches is (cwd, branch_name, start_point, force)
    assert any(
        branch == "new-feature" and start == "origin/parent-branch"
        for (_, branch, start, _) in fake_git_branch_ops.created_branches
    )

    # parent-branch should be force-updated to match remote
    assert any(
        branch == "parent-branch" and start == "origin/parent-branch" and force is True
        for (_, branch, start, force) in fake_git_branch_ops.created_branches
    )

    # Track was called with local branch name
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

    # The local branch should be created from remote (force=False)
    # created_branches is (cwd, branch_name, start_point, force)
    created_branches = [
        (branch, start, force) for (_, branch, start, force) in fake_git_branch_ops.created_branches
    ]
    assert ("parent-branch", "origin/parent-branch", False) in created_branches

    # No deletion since branch didn't exist
    assert "parent-branch" not in fake_git_branch_ops.deleted_branches

    # Track was called with local branch name
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


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
    # created_branches is (cwd, branch_name, start_point, force)
    created_branches = [branch for (_, branch, _, _) in fake_git_branch_ops.created_branches]
    assert "parent-branch" not in created_branches
    assert "new-feature" in created_branches
