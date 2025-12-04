"""Tests for FakeGit test infrastructure.

These tests verify that FakeGit correctly simulates git behavior,
tracks mutations, and provides reliable test doubles for CLI tests.
"""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit


def test_fake_gitops_list_worktrees() -> None:
    """Test that FakeGit lists pre-configured worktrees."""
    repo_root = Path("/repo")
    wt1 = Path("/repo/wt1")
    wt2 = Path("/repo/wt2")

    worktrees = {
        repo_root: [
            WorktreeInfo(path=repo_root, branch="main"),
            WorktreeInfo(path=wt1, branch="feature-1"),
            WorktreeInfo(path=wt2, branch="feature-2"),
        ]
    }

    git_ops = FakeGit(worktrees=worktrees)
    result = git_ops.list_worktrees(repo_root)

    assert len(result) == 3
    assert result[0].path == repo_root
    assert result[1].path == wt1
    assert result[2].path == wt2


def test_fake_gitops_add_worktree(tmp_path: Path) -> None:
    """Test that FakeGit can add worktrees (in-memory only, no filesystem operations)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_ops = FakeGit()

    new_wt = repo_root / "new-wt"
    git_ops.add_worktree(repo_root, new_wt, branch="new-branch")

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1
    assert worktrees[0].path == new_wt
    assert worktrees[0].branch == "new-branch"
    # FakeGit is purely in-memory - does not create directories


def test_fake_gitops_remove_worktree() -> None:
    """Test that FakeGit can remove worktrees."""
    repo_root = Path("/repo")
    wt1 = Path("/repo/wt1")

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1, branch="feature-1"),
            ]
        }
    )

    git_ops.remove_worktree(repo_root, wt1)

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 0


def test_fake_gitops_get_current_branch() -> None:
    """Test that FakeGit returns configured current branch."""
    cwd = Path("/repo")
    git_ops = FakeGit(current_branches={cwd: "feature-branch"})

    branch = git_ops.get_current_branch(cwd)
    assert branch == "feature-branch"


def test_fake_gitops_get_default_branch() -> None:
    """Test that FakeGit returns configured trunk branch."""
    repo_root = Path("/repo")
    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    branch = git_ops.detect_trunk_branch(repo_root)
    assert branch == "main"


def test_fake_gitops_get_git_common_dir() -> None:
    """Test that FakeGit returns configured git common dir."""
    cwd = Path("/repo")
    git_dir = Path("/repo/.git")

    git_ops = FakeGit(git_common_dirs={cwd: git_dir})

    common_dir = git_ops.get_git_common_dir(cwd)
    assert common_dir == git_dir


def test_fake_gitops_checkout_branch() -> None:
    """Test that FakeGit can checkout branches."""
    cwd = Path("/repo")
    git_ops = FakeGit(current_branches={cwd: "main"})

    git_ops.checkout_branch(cwd, "feature")

    assert git_ops.get_current_branch(cwd) == "feature"


def test_fake_gitops_delete_branch_tracking() -> None:
    """Test that FakeGit tracks deleted branches."""
    repo_root = Path("/repo")
    git_ops = FakeGit()

    git_ops.delete_branch_with_graphite(repo_root, "old-branch", force=True)

    assert "old-branch" in git_ops.deleted_branches


def test_fake_gitops_detached_head() -> None:
    """Test FakeGit with detached HEAD (None branch)."""
    cwd = Path("/repo")
    git_ops = FakeGit(current_branches={cwd: None})

    branch = git_ops.get_current_branch(cwd)
    assert branch is None


def test_fake_gitops_worktree_not_found() -> None:
    """Test FakeGit when worktree not found."""
    repo_root = Path("/repo")
    git_ops = FakeGit()

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 0


def test_fake_gitops_has_uncommitted_changes_no_changes() -> None:
    """Test has_uncommitted_changes returns False when no changes."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], [], [])})

    assert not git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_staged() -> None:
    """Test has_uncommitted_changes returns True when staged changes exist."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: (["file.txt"], [], [])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_modified() -> None:
    """Test has_uncommitted_changes returns True when modified changes exist."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], ["file.txt"], [])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_untracked() -> None:
    """Test has_uncommitted_changes returns True when untracked files exist."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], [], ["file.txt"])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_all_types() -> None:
    """Test has_uncommitted_changes with all types of changes."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: (["staged.txt"], ["modified.txt"], ["untracked.txt"])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_unknown_path() -> None:
    """Test has_uncommitted_changes returns False for unknown path."""
    cwd = Path("/repo")
    git_ops = FakeGit()

    assert not git_ops.has_uncommitted_changes(cwd)


# ========================================
# Critical Gap Tests: High-Risk Methods
# ========================================


def test_fake_gitops_get_file_status_empty() -> None:
    """Test get_file_status with no changes."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], [], [])})

    staged, modified, untracked = git_ops.get_file_status(cwd)

    assert staged == []
    assert modified == []
    assert untracked == []


def test_fake_gitops_get_file_status_staged_only() -> None:
    """Test get_file_status with only staged files."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: (["file.txt"], [], [])})

    staged, modified, untracked = git_ops.get_file_status(cwd)

    assert staged == ["file.txt"]
    assert modified == []
    assert untracked == []


def test_fake_gitops_get_file_status_modified_only() -> None:
    """Test get_file_status with only modified files."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], ["file.txt"], [])})

    staged, modified, untracked = git_ops.get_file_status(cwd)

    assert staged == []
    assert modified == ["file.txt"]
    assert untracked == []


def test_fake_gitops_get_file_status_untracked_only() -> None:
    """Test get_file_status with only untracked files."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: ([], [], ["file.txt"])})

    staged, modified, untracked = git_ops.get_file_status(cwd)

    assert staged == []
    assert modified == []
    assert untracked == ["file.txt"]


def test_fake_gitops_get_file_status_mixed() -> None:
    """Test get_file_status with all change types."""
    cwd = Path("/repo")
    git_ops = FakeGit(file_statuses={cwd: (["a.txt"], ["b.txt"], ["c.txt"])})

    staged, modified, untracked = git_ops.get_file_status(cwd)

    assert staged == ["a.txt"]
    assert modified == ["b.txt"]
    assert untracked == ["c.txt"]


def test_fake_gitops_move_worktree(tmp_path: Path) -> None:
    """Test move_worktree updates state (in-memory only, no filesystem operations)."""
    repo_root = tmp_path / "repo"
    old_wt = tmp_path / "old-wt"
    new_wt = tmp_path / "new-wt"

    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=old_wt, branch="feature", is_root=False)]}
    )

    git_ops.move_worktree(repo_root, old_wt, new_wt)

    # Verify state updated
    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1
    assert worktrees[0].path == new_wt
    assert worktrees[0].branch == "feature"

    # FakeGit is purely in-memory - does not rename directories


def test_fake_gitops_checkout_detached(tmp_path: Path) -> None:
    """Test checkout_detached sets branch to None and tracks operation."""
    cwd = tmp_path / "repo"
    git_ops = FakeGit(
        current_branches={cwd: "main"},
        worktrees={tmp_path: [WorktreeInfo(path=cwd, branch="main", is_root=True)]},
    )

    git_ops.checkout_detached(cwd, "abc123")

    # Verify branch is now None (detached HEAD)
    assert git_ops.get_current_branch(cwd) is None

    # Verify tracking property updated
    assert (cwd, "abc123") in git_ops.detached_checkouts

    # Verify worktree state updated
    worktrees = git_ops.list_worktrees(tmp_path)
    assert worktrees[0].branch is None


def test_fake_gitops_get_branch_head() -> None:
    """Test get_branch_head returns commit SHA from dict."""
    repo_root = Path("/repo")
    git_ops = FakeGit(branch_heads={"main": "abc123", "feature": "def456"})

    assert git_ops.get_branch_head(repo_root, "main") == "abc123"
    assert git_ops.get_branch_head(repo_root, "feature") == "def456"
    assert git_ops.get_branch_head(repo_root, "nonexistent") is None


def test_fake_gitops_get_commit_message() -> None:
    """Test get_commit_message returns message from dict."""
    repo_root = Path("/repo")
    git_ops = FakeGit(commit_messages={"abc123": "Initial commit", "def456": "Add feature"})

    assert git_ops.get_commit_message(repo_root, "abc123") == "Initial commit"
    assert git_ops.get_commit_message(repo_root, "def456") == "Add feature"
    assert git_ops.get_commit_message(repo_root, "unknown") is None


def test_fake_gitops_get_ahead_behind() -> None:
    """Test get_ahead_behind returns (ahead, behind) tuple."""
    cwd = Path("/repo")
    git_ops = FakeGit(
        ahead_behind={
            (cwd, "main"): (0, 0),
            (cwd, "feature"): (3, 1),
        }
    )

    assert git_ops.get_ahead_behind(cwd, "main") == (0, 0)
    assert git_ops.get_ahead_behind(cwd, "feature") == (3, 1)
    assert git_ops.get_ahead_behind(cwd, "unknown") == (0, 0)


def test_fake_gitops_get_recent_commits() -> None:
    """Test get_recent_commits returns commit list with limit."""
    cwd = Path("/repo")
    commits = [
        {"sha": "abc123", "message": "Commit 1"},
        {"sha": "def456", "message": "Commit 2"},
        {"sha": "ghi789", "message": "Commit 3"},
        {"sha": "jkl012", "message": "Commit 4"},
        {"sha": "mno345", "message": "Commit 5"},
        {"sha": "pqr678", "message": "Commit 6"},
    ]
    git_ops = FakeGit(recent_commits={cwd: commits})

    # Default limit is 5
    result = git_ops.get_recent_commits(cwd, limit=5)
    assert len(result) == 5
    assert result[0]["sha"] == "abc123"

    # Custom limit
    result = git_ops.get_recent_commits(cwd, limit=3)
    assert len(result) == 3

    # No commits configured
    result = git_ops.get_recent_commits(Path("/other"), limit=5)
    assert result == []


def test_fake_gitops_prune_worktrees_noop() -> None:
    """Test prune_worktrees is a no-op (doesn't crash)."""
    repo_root = Path("/repo")
    git_ops = FakeGit()

    # Should not raise
    git_ops.prune_worktrees(repo_root)


def test_fake_gitops_removed_worktrees_tracking() -> None:
    """Test removed_worktrees tracking property updates on remove."""
    repo_root = Path("/repo")
    wt1 = Path("/repo/wt1")
    wt2 = Path("/repo/wt2")

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1, branch="feat-1", is_root=False),
                WorktreeInfo(path=wt2, branch="feat-2", is_root=False),
            ]
        }
    )

    git_ops.remove_worktree(repo_root, wt1)
    git_ops.remove_worktree(repo_root, wt2)

    assert wt1 in git_ops.removed_worktrees
    assert wt2 in git_ops.removed_worktrees
    assert len(git_ops.removed_worktrees) == 2


def test_fake_gitops_checked_out_branches_tracking() -> None:
    """Test checked_out_branches tracking property updates on checkout."""
    cwd1 = Path("/repo/wt1")
    cwd2 = Path("/repo/wt2")

    git_ops = FakeGit(
        current_branches={cwd1: "main", cwd2: "feature"},
        worktrees={
            Path("/repo"): [
                WorktreeInfo(path=cwd1, branch="main", is_root=True),
                WorktreeInfo(path=cwd2, branch="feature", is_root=False),
            ]
        },
    )

    git_ops.checkout_branch(cwd1, "new-branch")

    assert (cwd1, "new-branch") in git_ops.checked_out_branches


def test_fake_gitops_detached_checkouts_tracking() -> None:
    """Test detached_checkouts tracking property updates on detached checkout."""
    cwd = Path("/repo")
    git_ops = FakeGit(
        current_branches={cwd: "main"},
        worktrees={Path("/repo"): [WorktreeInfo(path=cwd, branch="main", is_root=True)]},
    )

    git_ops.checkout_detached(cwd, "abc123")
    git_ops.checkout_detached(cwd, "def456")

    assert (cwd, "abc123") in git_ops.detached_checkouts
    assert (cwd, "def456") in git_ops.detached_checkouts
    assert len(git_ops.detached_checkouts) == 2


def test_fake_gitops_delete_branch_with_graphite_raises() -> None:
    """Test that FakeGit wraps CalledProcessError in RuntimeError on delete.

    This matches run_subprocess_with_context behavior where CalledProcessError
    is caught and re-raised as RuntimeError with the original in __cause__.
    """
    import subprocess

    import pytest

    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["gt", "delete", "test-branch"],
        stderr=None,
    )

    git_ops = FakeGit(
        delete_branch_raises={"test-branch": error},
    )

    repo_root = Path("/fake/repo")

    # Should raise RuntimeError wrapping the CalledProcessError
    with pytest.raises(RuntimeError) as exc_info:
        git_ops.delete_branch_with_graphite(repo_root, "test-branch", force=False)

    # Original CalledProcessError should be accessible via __cause__
    assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)
    assert exc_info.value.__cause__.returncode == 1
    assert "test-branch" in exc_info.value.__cause__.cmd

    # Other branches should not raise
    git_ops.delete_branch_with_graphite(repo_root, "other-branch", force=False)
    assert "other-branch" in git_ops.deleted_branches


def test_fake_git_is_worktree_clean_with_clean_worktree() -> None:
    """Test that is_worktree_clean returns True for clean worktree."""
    worktree_path = Path("/repo/worktree")
    git_ops = FakeGit(
        existing_paths={worktree_path},
    )

    result = git_ops.is_worktree_clean(worktree_path)
    assert result is True


def test_fake_git_is_worktree_clean_with_uncommitted_changes() -> None:
    """Test that is_worktree_clean returns False for dirty worktree."""
    worktree_path = Path("/repo/worktree")
    git_ops = FakeGit(
        existing_paths={worktree_path},
        dirty_worktrees={worktree_path},
    )

    result = git_ops.is_worktree_clean(worktree_path)
    assert result is False


def test_fake_git_is_worktree_clean_with_nonexistent_path() -> None:
    """Test that is_worktree_clean returns False for nonexistent path."""
    worktree_path = Path("/repo/nonexistent")
    git_ops = FakeGit()

    result = git_ops.is_worktree_clean(worktree_path)
    assert result is False


# ============================================================================
# Branch-Issue Association Tests
# ============================================================================


def test_fake_git_set_branch_issue() -> None:
    """Test set_branch_issue stores issue number for branch."""
    git_ops = FakeGit()

    git_ops.set_branch_issue(Path("/repo"), "feature-branch", 42)

    # Verify stored in fake
    result = git_ops.get_branch_issue(Path("/repo"), "feature-branch")
    assert result == 42


def test_fake_git_get_branch_issue_not_set() -> None:
    """Test get_branch_issue returns None when not set."""
    git_ops = FakeGit()

    result = git_ops.get_branch_issue(Path("/repo"), "feature-branch")

    assert result is None


def test_fake_git_set_branch_issue_multiple_branches() -> None:
    """Test setting issue numbers for multiple branches."""
    git_ops = FakeGit()

    git_ops.set_branch_issue(Path("/repo"), "branch-1", 10)
    git_ops.set_branch_issue(Path("/repo"), "branch-2", 20)
    git_ops.set_branch_issue(Path("/repo"), "branch-3", 30)

    assert git_ops.get_branch_issue(Path("/repo"), "branch-1") == 10
    assert git_ops.get_branch_issue(Path("/repo"), "branch-2") == 20
    assert git_ops.get_branch_issue(Path("/repo"), "branch-3") == 30


def test_fake_git_set_branch_issue_overwrites() -> None:
    """Test set_branch_issue overwrites existing association."""
    git_ops = FakeGit()

    git_ops.set_branch_issue(Path("/repo"), "feature", 10)
    git_ops.set_branch_issue(Path("/repo"), "feature", 20)

    # Should return latest value
    result = git_ops.get_branch_issue(Path("/repo"), "feature")
    assert result == 20


def test_fake_git_branch_issue_pre_configured() -> None:
    """Test FakeGit can be initialized with branch-issue associations."""
    branch_issues = {
        "feature-1": 42,
        "feature-2": 99,
    }
    git_ops = FakeGit(branch_issues=branch_issues)

    assert git_ops.get_branch_issue(Path("/repo"), "feature-1") == 42
    assert git_ops.get_branch_issue(Path("/repo"), "feature-2") == 99
    assert git_ops.get_branch_issue(Path("/repo"), "other-branch") is None


def test_fake_git_branch_issue_mixed_pre_configured_and_set() -> None:
    """Test mixing pre-configured and dynamically set branch-issue associations."""
    branch_issues = {"existing-branch": 100}
    git_ops = FakeGit(branch_issues=branch_issues)

    # Pre-configured should work
    assert git_ops.get_branch_issue(Path("/repo"), "existing-branch") == 100

    # Set new association
    git_ops.set_branch_issue(Path("/repo"), "new-branch", 200)

    # Both should be accessible
    assert git_ops.get_branch_issue(Path("/repo"), "existing-branch") == 100
    assert git_ops.get_branch_issue(Path("/repo"), "new-branch") == 200
