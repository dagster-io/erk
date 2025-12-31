"""Lightweight path utilities with minimal dependencies.

This module provides path utilities that can be used anywhere, including:
- Exec scripts without context injection
- Test utilities
- Lightweight CLI commands

These are pure functions that only depend on pathlib.
"""

from pathlib import Path


def find_git_root(start: Path) -> Path | None:
    """Find git repository root by walking up to find .git.

    Handles both regular repos (.git directory) and worktrees (.git file).

    Args:
        start: Starting directory to search from

    Returns:
        Path to repository root, or None if not in a git repository
    """
    current = start.resolve()
    while current != current.parent:
        git_path = current / ".git"
        if git_path.exists():  # Works for both .git dir and .git file (worktree)
            return current
        current = current.parent
    return None
