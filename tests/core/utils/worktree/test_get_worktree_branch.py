"""Tests for get_worktree_branch function."""

from pathlib import Path

from erk.core.worktree_utils import get_worktree_branch
from erk_shared.git.abc import WorktreeInfo


def test_returns_branch_for_worktree() -> None:
    """Test returns branch name for a given worktree path."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False),
    ]
    wt_path = Path("/repo/erks/feat")

    result = get_worktree_branch(worktrees, wt_path)

    assert result == "feature-x"


def test_returns_none_for_unknown_worktree() -> None:
    """Test returns None when worktree path is not found."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
    ]
    wt_path = Path("/repo/erks/unknown")

    result = get_worktree_branch(worktrees, wt_path)

    assert result is None


def test_returns_none_for_detached_head() -> None:
    """Test returns None when worktree is in detached HEAD state."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/detached"), None, False),
    ]
    wt_path = Path("/repo/erks/detached")

    result = get_worktree_branch(worktrees, wt_path)

    assert result is None


def test_handles_path_normalization() -> None:
    """Test handles different path representations correctly."""
    worktrees = [
        WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False),
    ]
    wt_path = Path("/repo/erks/feat/.")  # With trailing dot

    result = get_worktree_branch(worktrees, wt_path)

    assert result == "feature-x"
