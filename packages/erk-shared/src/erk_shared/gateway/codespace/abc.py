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
