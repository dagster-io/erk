"""Codespace execution abstraction for testing.

This module provides an ABC for codespace SSH operations to enable
testing without actually executing remote commands.
"""

from abc import ABC, abstractmethod
from typing import NoReturn


class Codespace(ABC):
    """Abstract codespace SSH executor for dependency injection."""

    @abstractmethod
    def exec_ssh_interactive(self, gh_name: str, remote_command: str) -> NoReturn:
        """Replace current process with SSH session to codespace.

        Uses os.execvp() to replace the current process, so this
        method never returns.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
            remote_command: Command to execute in the codespace

        Note:
            This method never returns - the process is replaced.
        """
        ...

    @abstractmethod
    def start_codespace(self, gh_name: str) -> None:
        """Start a stopped codespace.

        Ensures the codespace is running before attempting SSH connections.
        No-op if the codespace is already running.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
        """
        ...

    @abstractmethod
    def run_ssh_command(self, gh_name: str, remote_command: str) -> int:
        """Run SSH command in codespace and return exit code.

        Uses subprocess.run() to execute the command and wait for completion.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
            remote_command: Command to execute in the codespace

        Returns:
            Exit code from the remote command (0 for success)
        """
        ...

    @abstractmethod
    def get_repo_id(self, owner_repo: str) -> int:
        """Get GitHub repository database ID via REST API.

        Args:
            owner_repo: Repository in "owner/repo" format.

        Returns:
            The numeric repository ID.

        Raises:
            RuntimeError: If the API call fails.
        """
        ...

    @abstractmethod
    def create_codespace(
        self,
        *,
        repo_id: int,
        machine: str,
        display_name: str,
        branch: str | None,
    ) -> str:
        """Create a codespace via REST API.

        Args:
            repo_id: GitHub repository database ID.
            machine: Machine type for the codespace.
            display_name: Human-readable display name.
            branch: Branch to create codespace from, or None for default.

        Returns:
            The gh_name of the created codespace.

        Raises:
            RuntimeError: If the API call fails or response is malformed.
        """
        ...
