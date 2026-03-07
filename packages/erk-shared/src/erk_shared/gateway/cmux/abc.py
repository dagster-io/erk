"""Abstract interface for cmux workspace operations."""

from abc import ABC, abstractmethod


class Cmux(ABC):
    """Abstract base class for cmux workspace management.

    Wraps the cmux CLI tool for creating and renaming workspaces.
    """

    @abstractmethod
    def create_workspace(self, *, command: str) -> str:
        """Create a new cmux workspace with the given command.

        Args:
            command: Shell command to execute in the new workspace.

        Returns:
            Workspace reference string (e.g. "workspace-12345").

        Raises:
            RuntimeError: If workspace creation fails.
        """
        ...

    @abstractmethod
    def rename_workspace(self, *, workspace_ref: str, new_name: str) -> None:
        """Rename an existing cmux workspace.

        Args:
            workspace_ref: Reference to the workspace to rename.
            new_name: New name for the workspace.

        Raises:
            RuntimeError: If rename fails.
        """
        ...
