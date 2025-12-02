"""Abstract base class for GitHub Actions admin operations."""

from abc import ABC, abstractmethod
from typing import Any

from erk_shared.github.types import GitHubRepoLocation


class GitHubAdmin(ABC):
    """Abstract interface for GitHub Actions admin operations.

    All implementations (real and fake) must implement this interface.
    Provides methods for managing GitHub Actions workflow permissions.
    """

    @abstractmethod
    def get_workflow_permissions(self, location: GitHubRepoLocation) -> dict[str, Any]:
        """Get current workflow permissions from GitHub API.

        Args:
            location: GitHub repository location (local root + repo identity)

        Returns:
            Dict with keys:
            - default_workflow_permissions: "read" or "write"
            - can_approve_pull_request_reviews: bool

        Raises:
            RuntimeError: If gh CLI command fails
        """
        ...

    @abstractmethod
    def set_workflow_pr_permissions(self, location: GitHubRepoLocation, enabled: bool) -> None:
        """Enable or disable PR creation via workflow permissions API.

        Args:
            location: GitHub repository location (local root + repo identity)
            enabled: True to enable PR creation, False to disable

        Raises:
            RuntimeError: If gh CLI command fails
        """
        ...
