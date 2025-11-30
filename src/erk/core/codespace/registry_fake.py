"""In-memory fake implementation of CodespaceRegistry for testing."""

from datetime import datetime
from pathlib import Path

from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


class FakeCodespaceRegistry(CodespaceRegistry):
    """Test implementation that stores codespaces in memory.

    Use constructor injection to set up initial state for tests.

    Example:
        >>> registry = FakeCodespaceRegistry(codespaces={
        ...     "my-space": RegisteredCodespace(
        ...         friendly_name="my-space",
        ...         gh_name="schrockn-abc123",
        ...         ...
        ...     )
        ... })
    """

    def __init__(
        self,
        codespaces: dict[str, RegisteredCodespace] | None = None,
    ) -> None:
        """Initialize in-memory registry.

        Args:
            codespaces: Initial codespaces (None = empty registry that doesn't exist)
        """
        self._codespaces = codespaces.copy() if codespaces else {}
        self._exists = codespaces is not None

    def exists(self) -> bool:
        """Check if registry exists in memory."""
        return self._exists

    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces, sorted by last_connected_at desc."""
        codespaces = list(self._codespaces.values())

        # Sort: most recently connected first, never-connected at end
        # Use tuple: (has_connected, last_connected_at)
        # - has_connected: 1 for connected (sorts first), 0 for never (sorts last)
        # - last_connected_at: actual datetime for sorting within connected group
        def sort_key(cs: RegisteredCodespace) -> tuple[int, datetime]:
            if cs.last_connected_at is None:
                return (0, datetime.min)  # Never connected goes last
            return (1, cs.last_connected_at)  # Connected goes first, sorted by date

        return sorted(codespaces, key=sort_key, reverse=True)

    def get(self, friendly_name: str) -> RegisteredCodespace | None:
        """Get codespace by friendly name."""
        return self._codespaces.get(friendly_name)

    def register(self, codespace: RegisteredCodespace) -> None:
        """Register a new codespace."""
        if codespace.friendly_name in self._codespaces:
            raise ValueError(f"Codespace '{codespace.friendly_name}' already exists")

        self._codespaces[codespace.friendly_name] = codespace
        self._exists = True

    def update(self, codespace: RegisteredCodespace) -> None:
        """Update an existing codespace."""
        if codespace.friendly_name not in self._codespaces:
            raise KeyError(f"Codespace '{codespace.friendly_name}' not found")

        self._codespaces[codespace.friendly_name] = codespace

    def unregister(self, friendly_name: str) -> None:
        """Remove codespace from registry."""
        if friendly_name not in self._codespaces:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        del self._codespaces[friendly_name]

    def update_last_connected(self, friendly_name: str, timestamp: datetime) -> None:
        """Update last_connected_at timestamp."""
        codespace = self.get(friendly_name)
        if codespace is None:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        updated = RegisteredCodespace(
            friendly_name=codespace.friendly_name,
            gh_name=codespace.gh_name,
            repository=codespace.repository,
            branch=codespace.branch,
            machine_type=codespace.machine_type,
            configured=codespace.configured,
            registered_at=codespace.registered_at,
            last_connected_at=timestamp,
            notes=codespace.notes,
        )
        self._codespaces[friendly_name] = updated

    def mark_configured(self, friendly_name: str) -> None:
        """Mark codespace as configured."""
        codespace = self.get(friendly_name)
        if codespace is None:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        updated = RegisteredCodespace(
            friendly_name=codespace.friendly_name,
            gh_name=codespace.gh_name,
            repository=codespace.repository,
            branch=codespace.branch,
            machine_type=codespace.machine_type,
            configured=True,
            registered_at=codespace.registered_at,
            last_connected_at=codespace.last_connected_at,
            notes=codespace.notes,
        )
        self._codespaces[friendly_name] = updated

    def path(self) -> Path:
        """Get fake path for error messages."""
        return Path("/fake/erk/codespaces.toml")

    # Read-only property for test assertions
    @property
    def codespaces(self) -> dict[str, RegisteredCodespace]:
        """Read-only access to stored codespaces for test assertions."""
        return self._codespaces.copy()
