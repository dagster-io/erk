"""Fake implementation of PlannerRegistry for testing.

Stores planner data in memory without touching filesystem.
"""

from dataclasses import replace
from datetime import datetime

from erk.core.planner.registry_abc import PlannerRegistry
from erk.core.planner.types import RegisteredPlanner


class FakePlannerRegistry(PlannerRegistry):
    """In-memory implementation for testing.

    Provides mutation tracking via read-only properties for assertions.
    """

    def __init__(
        self,
        planners: list[RegisteredPlanner] | None = None,
        default_planner: str | None = None,
    ) -> None:
        """Initialize the fake registry.

        Args:
            planners: Initial list of planners
            default_planner: Name of the default planner (must exist in planners)
        """
        self._planners: dict[str, RegisteredPlanner] = {}
        self._default_planner: str | None = default_planner

        # Track mutations for assertions
        self._registered: list[RegisteredPlanner] = []
        self._unregistered: list[str] = []
        self._marked_configured: list[str] = []
        self._updated_last_connected: list[tuple[str, datetime]] = []
        self._set_defaults: list[str] = []

        if planners:
            for planner in planners:
                self._planners[planner.name] = planner

    def list_planners(self) -> list[RegisteredPlanner]:
        """List all registered planners."""
        return list(self._planners.values())

    def get(self, name: str) -> RegisteredPlanner | None:
        """Get a planner by name."""
        return self._planners.get(name)

    def get_default(self) -> RegisteredPlanner | None:
        """Get the default planner."""
        if self._default_planner is None:
            return None
        return self._planners.get(self._default_planner)

    def get_default_name(self) -> str | None:
        """Get the name of the default planner."""
        return self._default_planner

    def set_default(self, name: str) -> None:
        """Set the default planner."""
        if name not in self._planners:
            raise ValueError(f"No planner named '{name}' exists")
        self._default_planner = name
        self._set_defaults.append(name)

    def register(self, planner: RegisteredPlanner) -> None:
        """Register a new planner."""
        if planner.name in self._planners:
            raise ValueError(f"Planner '{planner.name}' already exists")
        self._planners[planner.name] = planner
        self._registered.append(planner)

    def unregister(self, name: str) -> None:
        """Remove a planner from the registry."""
        if name not in self._planners:
            raise ValueError(f"No planner named '{name}' exists")
        del self._planners[name]

        # Clear default if we're removing the default planner
        if self._default_planner == name:
            self._default_planner = None

        self._unregistered.append(name)

    def mark_configured(self, name: str) -> None:
        """Mark a planner as configured."""
        if name not in self._planners:
            raise ValueError(f"No planner named '{name}' exists")
        old_planner = self._planners[name]
        self._planners[name] = replace(old_planner, configured=True)
        self._marked_configured.append(name)

    def update_last_connected(self, name: str, timestamp: datetime) -> None:
        """Update the last connected timestamp for a planner."""
        if name not in self._planners:
            raise ValueError(f"No planner named '{name}' exists")
        old_planner = self._planners[name]
        self._planners[name] = replace(old_planner, last_connected_at=timestamp)
        self._updated_last_connected.append((name, timestamp))

    # Read-only mutation tracking properties for test assertions

    @property
    def registered_planners(self) -> list[RegisteredPlanner]:
        """Planners registered during test (for assertions)."""
        return list(self._registered)

    @property
    def unregistered_names(self) -> list[str]:
        """Names of planners unregistered during test (for assertions)."""
        return list(self._unregistered)

    @property
    def marked_configured_names(self) -> list[str]:
        """Names of planners marked as configured during test (for assertions)."""
        return list(self._marked_configured)

    @property
    def updated_connections(self) -> list[tuple[str, datetime]]:
        """(name, timestamp) pairs for last_connected updates (for assertions)."""
        return list(self._updated_last_connected)

    @property
    def set_default_history(self) -> list[str]:
        """History of set_default calls (for assertions)."""
        return list(self._set_defaults)
