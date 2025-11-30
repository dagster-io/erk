"""Abstract interface for GitHub Codespace operations."""

from abc import ABC, abstractmethod

from erk.core.codespace.types import GitHubCodespaceInfo


class CodespaceGitHub(ABC):
    """Abstract interface for GitHub codespace operations.

    Wraps `gh codespace` CLI commands with proper error handling.
    Provides dependency injection for testing without actual GitHub API calls.
    """

    @abstractmethod
    def list_codespaces(self) -> list[GitHubCodespaceInfo]:
        """List all codespaces for the authenticated user.

        Returns:
            List of codespace info from GitHub

        Raises:
            RuntimeError: If gh CLI fails
        """
        ...

    @abstractmethod
    def get_codespace(self, gh_name: str) -> GitHubCodespaceInfo | None:
        """Get information about a specific codespace.

        Args:
            gh_name: GitHub codespace name

        Returns:
            Codespace info if found, None if not exists

        Raises:
            RuntimeError: If gh CLI fails (for errors other than "not found")
        """
        ...

    @abstractmethod
    def create_codespace(
        self,
        repo: str,
        branch: str,
        machine_type: str = "standardLinux32gb",
    ) -> GitHubCodespaceInfo:
        """Create a new codespace.

        Args:
            repo: Repository in owner/repo format
            branch: Branch to create codespace from
            machine_type: VM type (default: standardLinux32gb)

        Returns:
            Created codespace info

        Raises:
            RuntimeError: If creation fails
        """
        ...

    @abstractmethod
    def wait_for_available(
        self,
        gh_name: str,
        timeout_seconds: int = 300,
    ) -> bool:
        """Wait for a codespace to become available.

        Args:
            gh_name: Codespace name
            timeout_seconds: Maximum wait time

        Returns:
            True if available, False if timeout
        """
        ...

    @abstractmethod
    def ssh_interactive(self, gh_name: str) -> int:
        """Open an interactive SSH session to the codespace.

        Uses subprocess.run (not os.execvp) so the caller continues after SSH exits.
        Useful for configure workflow where we need to prompt after SSH.

        Args:
            gh_name: Codespace name

        Returns:
            Exit code from SSH session
        """
        ...

    @abstractmethod
    def ssh_replace(self, gh_name: str) -> None:
        """Replace current process with SSH to codespace.

        Uses os.execvp - never returns on success.
        Useful for connect command where we just want to SSH in.

        Args:
            gh_name: Codespace name

        Note:
            This replaces the current process; it never returns on success.
        """
        ...
