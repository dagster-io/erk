"""Abstract base class for GitHub Actions admin operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from erk_shared.gateway.github.types import GitHubRepoLocation


@dataclass(frozen=True)
class AuthStatus:
    """Result of GitHub CLI authentication status check.

    Attributes:
        authenticated: True if user is logged in to GitHub
        username: GitHub username if authenticated, None otherwise
        error: Error message if check failed, None otherwise
    """

    authenticated: bool
    username: str | None
    error: str | None


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

    @abstractmethod
    def check_auth_status(self) -> AuthStatus:
        """Check GitHub CLI authentication status.

        Returns:
            AuthStatus with authentication details:
            - authenticated: True if logged in
            - username: GitHub username if authenticated
            - error: Error message if check failed
        """
        ...

    @abstractmethod
    def secret_exists(self, location: GitHubRepoLocation, secret_name: str) -> bool | None:
        """Check if a repository secret exists.

        Uses the GitHub Actions secrets API to check if a secret is defined.
        Does NOT return the secret value (which is never accessible via API).

        Args:
            location: GitHub repository location (local root + repo identity)
            secret_name: Name of the secret to check for

        Returns:
            True if secret exists, False if not, None if check failed (e.g., no permission)
        """
        ...

    @abstractmethod
    def get_variable(self, location: GitHubRepoLocation, name: str) -> str | None:
        """Get a repository variable value.

        Uses GET /repos/{owner}/{repo}/actions/variables/{name}.

        Args:
            location: GitHub repository location (local root + repo identity)
            name: Variable name to look up

        Returns:
            Variable value if found, None if not found
        """
        ...

    @abstractmethod
    def set_variable(self, location: GitHubRepoLocation, name: str, value: str) -> None:
        """Set a repository variable value.

        Creates or updates a repository variable using the GitHub Actions
        variables API. Uses PATCH if the variable exists, POST if it does not.

        Args:
            location: GitHub repository location (local root + repo identity)
            name: Variable name to set
            value: Variable value to set
        """
        ...
