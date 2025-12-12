"""Tests for find_worktree_containing_path function."""

from pathlib import Path

from erk.core.worktree_utils import find_worktree_containing_path
from erk_shared.git.abc import WorktreeInfo


def test_finds_exact_match() -> None:
    """Test finding exact worktree path match."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    target_path = Path("/repo/erks/feat")

    result = find_worktree_containing_path(worktrees, target_path)

    assert result == Path("/repo/erks/feat")


def test_finds_parent_worktree() -> None:
    """Test finding worktree when target is a subdirectory."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    target_path = Path("/repo/erks/feat/src/module")

    result = find_worktree_containing_path(worktrees, target_path)

    assert result == Path("/repo/erks/feat")


def test_returns_most_specific_match() -> None:
    """Test returns deepest match when worktrees are nested."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks"), "base", False),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    target_path = Path("/repo/erks/feat/src")

    result = find_worktree_containing_path(worktrees, target_path)

    # Should return the most specific (deepest) match
    assert result == Path("/repo/erks/feat")


def test_returns_none_when_not_found() -> None:
    """Test returns None when path is not in any worktree."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/erks/feat"), "feat", False),
    ]
    target_path = Path("/other/path")

    result = find_worktree_containing_path(worktrees, target_path)

    assert result is None


def test_handles_empty_worktree_list() -> None:
    """Test handles empty worktree list gracefully."""
    worktrees: list[WorktreeInfo] = []
    target_path = Path("/repo/src")

    result = find_worktree_containing_path(worktrees, target_path)

    assert result is None
