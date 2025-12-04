"""Abstract base class for GitHub workflow operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from erk_shared.github.types import GitHubRepoLocation


class GitHubWorkflowGateway(ABC):
    """Abstract interface for GitHub workflow operations.

    Consolidates workflow dispatch operations from GitHub + GitHubAdmin interfaces.
    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger a GitHub Actions workflow via gh CLI.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        ...

    # --- Admin operations (from GitHubAdmin) ---

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
