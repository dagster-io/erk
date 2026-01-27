"""Abstract base class for Git status operations.

This sub-gateway extracts status query operations from the main Git gateway,
including staged changes, uncommitted changes, file status, and conflict detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitStatusOps(ABC):
    """Abstract interface for Git status operations.

    This interface contains ONLY query operations (no mutations).
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes.

        Args:
            repo_root: Path to the git repository root

        Returns:
            True if there are staged changes, False otherwise
        """
        ...

    @abstractmethod
    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes.

        Uses git status --porcelain to detect any uncommitted changes.
        Returns False if git command fails (worktree might be in invalid state).

        Args:
            cwd: Working directory to check

        Returns:
            True if there are any uncommitted changes (staged, modified, or untracked)
        """
        ...

    @abstractmethod
    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files.

        Args:
            cwd: Working directory

        Returns:
            Tuple of (staged, modified, untracked) file lists
        """
        ...

    @abstractmethod
    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree.

        Args:
            cwd: Working directory
            base_branch: Base branch to merge into
            head_branch: Head branch to merge from

        Returns:
            True if merge would have conflicts, False otherwise
        """
        ...

    @abstractmethod
    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get list of files with merge conflicts from git status --porcelain.

        Returns file paths with conflict status codes (UU, AA, DD, AU, UA, DU, UD).

        Args:
            cwd: Working directory

        Returns:
            List of file paths with conflicts
        """
        ...
