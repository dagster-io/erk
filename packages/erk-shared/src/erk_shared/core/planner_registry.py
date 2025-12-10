"""Planner box registry abstraction - ABC and types.

This module provides the abstract interface for planner registry operations
and the RegisteredPlanner type.

A planner box is a registered GitHub Codespace dedicated to remote planning
with Claude Code. The real implementation remains in erk.core.planner.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegisteredPlanner:
    """A registered planner box (GitHub Codespace for planning).

    Attributes:
        name: Friendly name for the planner (used as key)
        gh_name: GitHub codespace name (e.g., "schrockn-curly-rotary-phone-abc123")
        repository: Repository the codespace belongs to (e.g., "dagster-io/dagster")
        configured: Whether the configure wizard has been completed
        registered_at: When the planner was registered
        last_connected_at: When the planner was last connected to (None if never)
    """

    name: str
    gh_name: str
    repository: str
    configured: bool
    registered_at: datetime
    last_connected_at: datetime | None = None


class PlannerRegistry(ABC):
    """Abstract interface for planner registry operations.

    Manages registration and configuration of planner boxes
    (GitHub Codespaces dedicated to remote planning).
    """

    @abstractmethod
    def list_planners(self) -> list[RegisteredPlanner]:
        """List all registered planners.

        Returns:
            List of registered planners, may be empty
        """
        ...

    @abstractmethod
    def get(self, name: str) -> RegisteredPlanner | None:
        """Get a planner by name.

        Args:
            name: Friendly name of the planner

        Returns:
            RegisteredPlanner if found, None otherwise
        """
        ...

    @abstractmethod
    def get_default(self) -> RegisteredPlanner | None:
        """Get the default planner.

        Returns:
            The default planner if one is set and exists, None otherwise
        """
        ...

    @abstractmethod
    def get_default_name(self) -> str | None:
        """Get the name of the default planner.

        Returns:
            The default planner name if set, None otherwise
        """
        ...

    @abstractmethod
    def set_default(self, name: str) -> None:
        """Set the default planner.

        Args:
            name: Name of the planner to set as default

        Raises:
            ValueError: If no planner with that name exists
        """
        ...

    @abstractmethod
    def register(self, planner: RegisteredPlanner) -> None:
        """Register a new planner.

        Args:
            planner: The planner to register

        Raises:
            ValueError: If a planner with that name already exists
        """
        ...

    @abstractmethod
    def unregister(self, name: str) -> None:
        """Remove a planner from the registry.

        Args:
            name: Name of the planner to remove

        Raises:
            ValueError: If no planner with that name exists
        """
        ...

    @abstractmethod
    def mark_configured(self, name: str) -> None:
        """Mark a planner as configured.

        Args:
            name: Name of the planner to mark as configured

        Raises:
            ValueError: If no planner with that name exists
        """
        ...

    @abstractmethod
    def update_last_connected(self, name: str, timestamp: datetime) -> None:
        """Update the last connected timestamp for a planner.

        Args:
            name: Name of the planner
            timestamp: The new last_connected_at timestamp

        Raises:
            ValueError: If no planner with that name exists
        """
        ...
