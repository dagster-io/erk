"""Abstract base class for GitHub authentication operations."""

from abc import ABC, abstractmethod


class GitHubAuthGateway(ABC):
    """Abstract interface for GitHub authentication operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        This is a LBYL check to validate GitHub CLI authentication before operations
        that require it.

        Returns:
            Tuple of (is_authenticated, username, hostname):
            - is_authenticated: True if gh CLI is authenticated
            - username: Authenticated username (e.g., "octocat") or None if not authenticated
            - hostname: GitHub hostname (e.g., "github.com") or None

        Example:
            >>> github.auth.check_auth_status()
            (True, "octocat", "github.com")
            >>> # If not authenticated:
            (False, None, None)
        """
        ...

    @abstractmethod
    def get_current_username(self) -> str | None:
        """Get the current authenticated GitHub username.

        Returns:
            GitHub username if authenticated, None if not authenticated

        Note:
            This is a global operation (not repository-specific).
            Used for attribution in plan creation (created_by field).
        """
        ...
