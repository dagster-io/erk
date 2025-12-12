"""Tests for find_current_worktree function."""

from pathlib import Path

from erk.core.worktree_utils import find_current_worktree
from erk_shared.git.abc import WorktreeInfo


def test_finds_current_worktree() -> None:
    """Test finding the WorktreeInfo for current directory."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    current_dir = Path("/repo/erks/feat/src")

    result = find_current_worktree(worktrees, current_dir)

    assert result is not None
    assert result.path == Path("/repo/erks/feat")
    assert result.branch == "feat"
    assert result.is_root is False


def test_returns_none_when_not_in_worktree() -> None:
    """Test returns None when current directory is not in any worktree."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
    ]
    current_dir = Path("/other/path")

    result = find_current_worktree(worktrees, current_dir)

    assert result is None


def test_returns_root_worktree_info() -> None:
    """Test correctly returns root worktree info."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    current_dir = Path("/repo/src")

    result = find_current_worktree(worktrees, current_dir)

    assert result is not None
    assert result.path == Path("/repo")
    assert result.branch == "main"
    assert result.is_root is True
