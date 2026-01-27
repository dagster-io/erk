"""Abstract base class for Git tag operations.

This sub-gateway extracts tag operations from the main Git gateway,
including tag existence checks, creation, and pushing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitTagOps(ABC):
    """Abstract interface for Git tag operations.

    This interface contains both query and mutation operations for tags.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to check (e.g., 'v1.0.0')

        Returns:
            True if the tag exists, False otherwise
        """
        ...

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to create (e.g., 'v1.0.0')
            message: Tag message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote.

        Args:
            repo_root: Path to the repository root
            remote: Remote name (e.g., 'origin')
            tag_name: Tag name to push

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...
