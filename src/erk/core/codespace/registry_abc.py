"""Abstract interface for codespace registry operations."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from erk.core.codespace.types import RegisteredCodespace


class CodespaceRegistry(ABC):
    """Abstract interface for codespace registry operations.

    Provides dependency injection for codespace tracking, enabling
    in-memory implementations for tests without touching filesystem.

    The registry stores "pet" codespaces that the user has chosen to track
    with friendly names for easy access.
    """

    @abstractmethod
    def exists(self) -> bool:
        """Check if the registry file exists."""
        ...

    @abstractmethod
    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces.

        Returns:
            List of registered codespaces, sorted by last_connected_at desc
            (most recently used first), with never-connected at the end.
        """
        ...

    @abstractmethod
    def get(self, friendly_name: str) -> RegisteredCodespace | None:
        """Get a registered codespace by its friendly name.

        Args:
            friendly_name: User-chosen friendly name

        Returns:
            RegisteredCodespace if found, None otherwise
        """
        ...

    @abstractmethod
    def register(self, codespace: RegisteredCodespace) -> None:
        """Register a new codespace.

        Args:
            codespace: Codespace to register

        Raises:
            ValueError: If codespace with same friendly_name already exists
        """
        ...

    @abstractmethod
    def update(self, codespace: RegisteredCodespace) -> None:
        """Update an existing codespace entry.

        Args:
            codespace: Codespace with updated fields (matched by friendly_name)

        Raises:
            KeyError: If codespace not found in registry
        """
        ...

    @abstractmethod
    def unregister(self, friendly_name: str) -> None:
        """Remove a codespace from the registry.

        Args:
            friendly_name: Friendly name of codespace to remove

        Raises:
            KeyError: If codespace not found
        """
        ...

    @abstractmethod
    def update_last_connected(self, friendly_name: str, timestamp: datetime) -> None:
        """Update the last_connected_at timestamp for a codespace.

        Args:
            friendly_name: Codespace to update
            timestamp: New last_connected_at value

        Raises:
            KeyError: If codespace not found
        """
        ...

    @abstractmethod
    def mark_configured(self, friendly_name: str) -> None:
        """Mark a codespace as configured.

        Args:
            friendly_name: Codespace to mark as configured

        Raises:
            KeyError: If codespace not found
        """
        ...

    @abstractmethod
    def path(self) -> Path:
        """Get the path to the registry file.

        Returns:
            Path to registry file (for error messages and debugging)
        """
        ...
