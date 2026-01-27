"""Abstract base class for Git rebase operations.

This sub-gateway extracts rebase operations from the main Git gateway,
including rebase_onto, rebase_continue, rebase_abort, and is_rebase_in_progress.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.git.abc import RebaseResult


class GitRebaseOps(ABC):
    """Abstract interface for Git rebase operations.

    This interface contains both mutation and query operations for rebasing.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase the current branch onto a target ref.

        Runs `git rebase <target_ref>` to replay current branch commits on top
        of the target ref.

        Args:
            cwd: Working directory (must be in a git repository)
            target_ref: The ref to rebase onto (e.g., "origin/main", branch name)

        Returns:
            RebaseResult with success flag and any conflict files.
            If conflicts occur, the rebase will be left in progress.
        """
        ...

    @abstractmethod
    def rebase_continue(self, cwd: Path) -> None:
        """Continue an in-progress rebase (git rebase --continue).

        Args:
            cwd: Working directory

        Raises:
            subprocess.CalledProcessError: If continue fails (e.g., unresolved conflicts)
        """
        ...

    @abstractmethod
    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation.

        Runs `git rebase --abort` to cancel a rebase that has conflicts
        and restore the branch to its original state.

        Args:
            cwd: Working directory (must have a rebase in progress)

        Raises:
            subprocess.CalledProcessError: If no rebase is in progress
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (.git/rebase-merge or .git/rebase-apply).

        Handles worktrees by checking git common dir.

        Args:
            cwd: Working directory

        Returns:
            True if a rebase is in progress
        """
        ...
