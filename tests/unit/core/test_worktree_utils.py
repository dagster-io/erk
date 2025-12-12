"""Tests for worktree_utils functions."""

from pathlib import Path

from erk.core.worktree_utils import (
    compute_relative_path_in_worktree,
    find_worktree_containing_path,
)
from erk_shared.git.abc import WorktreeInfo


def test_compute_relative_path_returns_none_when_at_worktree_root() -> None:
    """Returns None when current_dir is at the worktree root."""
    worktrees = [
        WorktreeInfo(path=Path("/repo/worktrees/feat"), branch="feat", is_root=False),
    ]
    # When at root, relative path is None
    result = compute_relative_path_in_worktree(worktrees, Path("/repo/worktrees/feat"))
    assert result is None


def test_compute_relative_path_returns_none_when_not_in_worktree() -> None:
    """Returns None when current_dir is not in any known worktree."""
    worktrees = [
        WorktreeInfo(path=Path("/repo/worktrees/feat"), branch="feat", is_root=False),
    ]
    # Path not in any worktree
    result = compute_relative_path_in_worktree(worktrees, Path("/other/path"))
    assert result is None


def test_compute_relative_path_returns_subpath(tmp_path: Path) -> None:
    """Returns relative path when in a subdirectory of a worktree."""
    # Create real directories for path resolution
    worktree_root = tmp_path / "worktrees" / "feat"
    worktree_root.mkdir(parents=True)
    subdir = worktree_root / "src" / "lib"
    subdir.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=worktree_root, branch="feat", is_root=False),
    ]
    result = compute_relative_path_in_worktree(worktrees, subdir)
    assert result == Path("src/lib")


def test_compute_relative_path_handles_nested_worktrees(tmp_path: Path) -> None:
    """Returns relative path from most specific (deepest) worktree match."""
    # Create nested worktree structure
    root_wt = tmp_path / "repo"
    root_wt.mkdir(parents=True)
    nested_wt = root_wt / "worktrees" / "nested"
    nested_wt.mkdir(parents=True)
    subdir = nested_wt / "src"
    subdir.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=root_wt, branch="main", is_root=True),
        WorktreeInfo(path=nested_wt, branch="nested", is_root=False),
    ]

    # Should find the nested worktree (deeper match)
    result = compute_relative_path_in_worktree(worktrees, subdir)
    assert result == Path("src")


def test_compute_relative_path_handles_deeply_nested_paths(tmp_path: Path) -> None:
    """Returns deeply nested relative path correctly."""
    worktree_root = tmp_path / "worktrees" / "feat"
    worktree_root.mkdir(parents=True)
    deep_path = worktree_root / "src" / "components" / "ui" / "buttons"
    deep_path.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=worktree_root, branch="feat", is_root=False),
    ]
    result = compute_relative_path_in_worktree(worktrees, deep_path)
    assert result == Path("src/components/ui/buttons")


def test_find_worktree_containing_path_returns_deepest_match(tmp_path: Path) -> None:
    """find_worktree_containing_path returns the most specific match."""
    root_wt = tmp_path / "repo"
    root_wt.mkdir(parents=True)
    nested_wt = root_wt / "worktrees" / "feat"
    nested_wt.mkdir(parents=True)
    target = nested_wt / "src"
    target.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=root_wt, branch="main", is_root=True),
        WorktreeInfo(path=nested_wt, branch="feat", is_root=False),
    ]

    result = find_worktree_containing_path(worktrees, target)
    assert result == nested_wt.resolve()


def test_find_worktree_containing_path_returns_none_for_unrelated_path() -> None:
    """find_worktree_containing_path returns None for paths not in any worktree."""
    worktrees = [
        WorktreeInfo(path=Path("/repo"), branch="main", is_root=True),
    ]
    result = find_worktree_containing_path(worktrees, Path("/other/path"))
    assert result is None
