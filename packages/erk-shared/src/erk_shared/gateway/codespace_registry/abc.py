"""Codespace registry abstraction - ABC and types.

This module provides the abstract interface for codespace registry operations
and the RegisteredCodespace type.

A codespace is a registered GitHub Codespace that can be used for running
Claude Code remotely. Unlike planners, codespaces have a simpler structure
with just name, gh_name, and created_at fields.

The ABC is read-only. Mutation operations are standalone functions in the
real implementation module (real.py).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegisteredCodespace:
    """A registered codespace (GitHub Codespace for remote execution).

    Attributes:
        name: Friendly name for the codespace (used as key)
        gh_name: GitHub codespace name (e.g., "user-codespace-abc123")
        created_at: When the codespace was registered
    """

    name: str
    gh_name: str
    created_at: datetime


class CodespaceRegistry(ABC):
    """Abstract interface for codespace registry read operations.

    Manages lookup of codespaces (GitHub Codespaces for remote Claude execution).

    This is a read-only interface. Mutation operations (register, unregister,
    set_default) are standalone functions in the real implementation module.
    """

    @abstractmethod
    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces.

        Returns:
            List of registered codespaces, may be empty
        """
        ...

    @abstractmethod
    def get(self, name: str) -> RegisteredCodespace | None:
        """Get a codespace by name.

        Args:
            name: Friendly name of the codespace

        Returns:
            RegisteredCodespace if found, None otherwise
        """
        ...

    @abstractmethod
    def get_default(self) -> RegisteredCodespace | None:
        """Get the default codespace.

        Returns:
            The default codespace if one is set and exists, None otherwise
        """
        ...

    @abstractmethod
    def get_default_name(self) -> str | None:
        """Get the name of the default codespace.

        Returns:
            The default codespace name if set, None otherwise
        """
        ...
