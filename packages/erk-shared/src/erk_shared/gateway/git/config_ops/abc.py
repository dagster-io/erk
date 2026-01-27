"""Abstract interface for git configuration operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitConfigOps(ABC):
    """Abstract interface for Git configuration operations.

    This interface contains both mutation and query operations for git config.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value.

        Args:
            cwd: Working directory
            key: Configuration key (e.g., "user.name", "user.email")
            value: Configuration value
            scope: Configuration scope ("local", "global", or "system")

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name.

        Args:
            cwd: Working directory

        Returns:
            The configured user.name, or None if not set
        """
        ...
