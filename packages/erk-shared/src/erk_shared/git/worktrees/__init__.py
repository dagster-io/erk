"""Git worktree operations integration.

This module provides a focused abstraction over git worktree subprocess calls.
Part of the Git gateway refactoring to split the monolithic Git ABC into
smaller, focused integrations.
"""

from erk_shared.git.worktrees.abc import GitWorktrees

__all__ = ["GitWorktrees"]
