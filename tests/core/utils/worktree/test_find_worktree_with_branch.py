"""Tests for find_worktree_with_branch function."""

from pathlib import Path

from erk.core.worktree_utils import find_worktree_with_branch
from erk_shared.git.abc import WorktreeInfo


def test_finds_worktree_with_branch() -> None:
    """Test finds worktree path for a given branch."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False),
    ]

    result = find_worktree_with_branch(worktrees, "feature-x")

    assert result == Path("/repo/erks/feat")


def test_returns_none_when_branch_not_found() -> None:
    """Test returns None when branch is not in any worktree."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False),
    ]

    result = find_worktree_with_branch(worktrees, "unknown-branch")

    assert result is None


def test_finds_root_worktree_branch() -> None:
    """Test finds root worktree by branch name."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False),
    ]

    result = find_worktree_with_branch(worktrees, "main")

    assert result == Path("/repo")


def test_handles_empty_worktree_list() -> None:
    """Test handles empty worktree list gracefully."""
    worktrees: list[WorktreeInfo] = []

    result = find_worktree_with_branch(worktrees, "any-branch")

    assert result is None
