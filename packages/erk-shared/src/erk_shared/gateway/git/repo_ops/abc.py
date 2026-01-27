"""Abstract interface for git repository operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitRepoOps(ABC):
    """Abstract interface for Git repository location operations.

    This interface contains query operations for repository structure.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory.

        Uses `git rev-parse --show-toplevel` to find the repository root.

        Args:
            cwd: Working directory to start search from

        Returns:
            Path to the repository root

        Raises:
            subprocess.CalledProcessError: If not in a git repository
        """
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory.

        Returns the path to the shared .git directory. For worktrees, this
        returns the main repository's .git directory. Returns None gracefully
        if not in a git repository (unlike get_repository_root which raises).

        Args:
            cwd: Working directory

        Returns:
            Path to the .git common directory, or None if not in a git repo
        """
        ...
