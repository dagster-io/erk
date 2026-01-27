"""Integration tests for RealGitBranchOps.

Tests verify that RealGitBranchOps correctly executes git branch operations
using actual git subprocess calls.
"""

import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.git.branch_ops.real import RealGitBranchOps
from erk_shared.gateway.git.real import RealGit
from tests.integration.conftest import GitBranchOpsSetup, init_git_repo


def test_create_branch_creates_new_branch(git_branch_ops: GitBranchOpsSetup) -> None:
    """Test that create_branch creates a new branch from the specified start point."""
    branch_ops, git, repo = git_branch_ops

    # Act
    branch_ops.create_branch(repo, "feature-branch", "main", force=False)

    # Assert
    branches = git.list_local_branches(repo)
    assert "feature-branch" in branches


def test_create_branch_from_specific_commit(git_branch_ops: GitBranchOpsSetup) -> None:
    """Test that create_branch can create a branch from a specific commit."""
    branch_ops, git, repo = git_branch_ops

    # Arrange: Create a second commit
    test_file = repo / "second.txt"
    test_file.write_text("second commit", encoding="utf-8")
    subprocess.run(["git", "add", "second.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], cwd=repo, check=True)

    # Get the first commit SHA
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    first_commit = result.stdout.strip()

    # Act: Create branch from first commit
    branch_ops.create_branch(repo, "from-first", first_commit, force=False)

    # Assert: Branch exists and points to first commit
    branches = git.list_local_branches(repo)
    assert "from-first" in branches

    result = subprocess.run(
        ["git", "rev-parse", "from-first"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == first_commit


def test_delete_branch_with_force_false_fails_on_unmerged(
    git_branch_ops: GitBranchOpsSetup,
) -> None:
    """Test that delete_branch with force=False fails on unmerged branch."""
    branch_ops, git, repo = git_branch_ops

    # Arrange: Create a branch with unmerged commits
    subprocess.run(["git", "checkout", "-b", "unmerged-branch"], cwd=repo, check=True)
    test_file = repo / "unmerged.txt"
    test_file.write_text("unmerged content", encoding="utf-8")
    subprocess.run(["git", "add", "unmerged.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Unmerged commit"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)

    # Act & Assert: Should raise error for unmerged branch
    with pytest.raises(RuntimeError, match="delete branch"):
        branch_ops.delete_branch(repo, "unmerged-branch", force=False)

    # Branch should still exist
    branches = git.list_local_branches(repo)
    assert "unmerged-branch" in branches


def test_delete_branch_with_force_true_deletes_unmerged(
    git_branch_ops: GitBranchOpsSetup,
) -> None:
    """Test that delete_branch with force=True deletes unmerged branch."""
    branch_ops, git, repo = git_branch_ops

    # Arrange: Create a branch with unmerged commits
    subprocess.run(["git", "checkout", "-b", "unmerged-branch"], cwd=repo, check=True)
    test_file = repo / "unmerged.txt"
    test_file.write_text("unmerged content", encoding="utf-8")
    subprocess.run(["git", "add", "unmerged.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Unmerged commit"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)

    # Act: Force delete the unmerged branch
    branch_ops.delete_branch(repo, "unmerged-branch", force=True)

    # Assert: Branch should be gone
    branches = git.list_local_branches(repo)
    assert "unmerged-branch" not in branches


def test_checkout_branch_switches_working_directory(
    git_branch_ops: GitBranchOpsSetup,
) -> None:
    """Test that checkout_branch switches to the specified branch."""
    branch_ops, git, repo = git_branch_ops

    # Arrange: Create a new branch
    subprocess.run(["git", "branch", "feature-branch"], cwd=repo, check=True)

    # Act
    branch_ops.checkout_branch(repo, "feature-branch")

    # Assert
    current = git.get_current_branch(repo)
    assert current == "feature-branch"


def test_checkout_detached_moves_to_detached_head(
    git_branch_ops: GitBranchOpsSetup,
) -> None:
    """Test that checkout_detached creates a detached HEAD state."""
    branch_ops, git, repo = git_branch_ops

    # Arrange: Get current commit
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_sha = result.stdout.strip()

    # Act
    branch_ops.checkout_detached(repo, commit_sha)

    # Assert: Should be in detached HEAD state
    current = git.get_current_branch(repo)
    assert current is None  # Detached HEAD returns None


def test_create_tracking_branch_from_remote(tmp_path: Path) -> None:
    """Test that create_tracking_branch creates a local branch tracking remote."""
    # Arrange: Set up a "remote" repo and clone it
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    init_git_repo(remote_repo, "main")

    # Create a feature branch on remote
    subprocess.run(["git", "branch", "remote-feature"], cwd=remote_repo, check=True)

    # Clone the remote
    local_repo = tmp_path / "local"
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    branch_ops = RealGitBranchOps()
    git = RealGit()

    # Act: Create tracking branch
    branch_ops.create_tracking_branch(local_repo, "local-feature", "origin/remote-feature")

    # Assert: Local branch exists and tracks remote
    branches = git.list_local_branches(local_repo)
    assert "local-feature" in branches

    # Verify tracking configuration
    result = subprocess.run(
        ["git", "config", "--get", "branch.local-feature.remote"],
        cwd=local_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "origin"


def test_delete_branch_idempotent_when_branch_missing(
    git_branch_ops: GitBranchOpsSetup,
) -> None:
    """Test that delete_branch succeeds when branch doesn't exist (idempotent)."""
    branch_ops, git, repo = git_branch_ops

    # Act: Try to delete a branch that doesn't exist
    # Should not raise - idempotent behavior
    branch_ops.delete_branch(repo, "nonexistent-branch", force=False)

    # Assert: No error was raised, operation succeeded
    # (If we got here, the test passed)
