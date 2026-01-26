"""Unit tests for GraphiteBranchManager."""

from pathlib import Path

from erk_shared.branch_manager.graphite import GraphiteBranchManager
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata

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


def test_create_branch_auto_fixes_diverged_parent() -> None:
    """Test that create_branch auto-fixes diverged parent before tracking child.

    When the parent branch has a mismatch between actual git SHA and Graphite's
    tracked revision, create_branch should checkout the parent, retrack it,
    then proceed with tracking the child.
    """
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "actual-sha-after-rebase",
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()

    # Parent branch is diverged: tracked_revision != commit_sha
    branches = {
        "main": BranchMetadata.trunk("main", children=["parent-branch"], commit_sha="main-sha"),
        "parent-branch": BranchMetadata.branch(
            "parent-branch",
            "main",
            commit_sha="actual-sha-after-rebase",  # Actual git SHA
            tracked_revision="stale-sha-from-cache",  # Graphite's stale cache
        ),
    }
    fake_graphite = FakeGraphite(branches=branches)
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # Create branch from diverged parent
    manager.create_branch(REPO_ROOT, "new-feature", "parent-branch")

    # Parent branch should have been retracked
    assert any(
        branch == "parent-branch" for (_, branch) in fake_graphite_branch_ops.retrack_branch_calls
    )

    # New feature should be tracked
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )


def test_create_branch_skips_retrack_when_parent_not_diverged() -> None:
    """Test that create_branch does not retrack parent when not diverged."""
    fake_git = FakeGit(
        current_branches={REPO_ROOT: "main"},
        worktrees={REPO_ROOT: [WorktreeInfo(path=REPO_ROOT, branch="main", is_root=True)]},
        local_branches={REPO_ROOT: ["main", "parent-branch"]},
        branch_heads={
            "parent-branch": "same-sha",
        },
    )
    fake_git_branch_ops = fake_git.create_linked_branch_ops()

    # Parent branch is NOT diverged: tracked_revision == commit_sha
    branches = {
        "main": BranchMetadata.trunk("main", children=["parent-branch"], commit_sha="main-sha"),
        "parent-branch": BranchMetadata.branch(
            "parent-branch",
            "main",
            commit_sha="same-sha",  # Same as tracked
            tracked_revision="same-sha",
        ),
    }
    fake_graphite = FakeGraphite(branches=branches)
    fake_graphite_branch_ops = fake_graphite.create_linked_branch_ops()
    fake_github = FakeGitHub()

    manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,
        github=fake_github,
    )

    # Create branch from non-diverged parent
    manager.create_branch(REPO_ROOT, "new-feature", "parent-branch")

    # Parent should NOT have been retracked (no divergence)
    assert len(fake_graphite_branch_ops.retrack_branch_calls) == 0

    # New feature should still be tracked
    assert any(
        branch == "new-feature" and parent == "parent-branch"
        for (_, branch, parent) in fake_graphite.track_branch_calls
    )
