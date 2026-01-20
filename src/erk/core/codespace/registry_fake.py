"""Fake implementation of CodespaceRegistry for testing.

Stores codespace data in memory without touching filesystem.
"""

from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


class FakeCodespaceRegistry(CodespaceRegistry):
    """In-memory implementation for testing.

    Implements the read-only ABC and provides additional mutation methods
    for test setup convenience. Mutation tracking via read-only properties
    enables assertions in tests.
    """

    def __init__(
        self,
        *,
        codespaces: list[RegisteredCodespace] | None = None,
        default_codespace: str | None = None,
    ) -> None:
        """Initialize the fake registry.

        Args:
            codespaces: Initial list of codespaces
            default_codespace: Name of the default codespace (must exist in codespaces)
        """
        self._codespaces: dict[str, RegisteredCodespace] = {}
        self._default_codespace: str | None = default_codespace

        # Track mutations for assertions
        self._registered: list[RegisteredCodespace] = []
        self._unregistered: list[str] = []
        self._set_defaults: list[str] = []

        if codespaces:
            for codespace in codespaces:
                self._codespaces[codespace.name] = codespace

    # ABC read-only methods

    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces."""
        return list(self._codespaces.values())

    def get(self, name: str) -> RegisteredCodespace | None:
        """Get a codespace by name."""
        return self._codespaces.get(name)

    def get_default(self) -> RegisteredCodespace | None:
        """Get the default codespace."""
        if self._default_codespace is None:
            return None
        return self._codespaces.get(self._default_codespace)

    def get_default_name(self) -> str | None:
        """Get the name of the default codespace."""
        return self._default_codespace

    # Test helper methods (not part of ABC)

    def register(self, codespace: RegisteredCodespace) -> None:
        """Register a new codespace (test helper, not ABC method)."""
        if codespace.name in self._codespaces:
            raise ValueError(f"Codespace '{codespace.name}' already exists")
        self._codespaces[codespace.name] = codespace
        self._registered.append(codespace)

    def unregister(self, name: str) -> None:
        """Remove a codespace from the registry (test helper, not ABC method)."""
        if name not in self._codespaces:
            raise ValueError(f"No codespace named '{name}' exists")
        del self._codespaces[name]

        # Clear default if we're removing the default codespace
        if self._default_codespace == name:
            self._default_codespace = None

        self._unregistered.append(name)

    def set_default(self, name: str) -> None:
        """Set the default codespace (test helper, not ABC method)."""
        if name not in self._codespaces:
            raise ValueError(f"No codespace named '{name}' exists")
        self._default_codespace = name
        self._set_defaults.append(name)

    # Read-only mutation tracking properties for test assertions

    @property
    def registered_codespaces(self) -> list[RegisteredCodespace]:
        """Codespaces registered during test (for assertions)."""
        return list(self._registered)

    @property
    def unregistered_names(self) -> list[str]:
        """Names of codespaces unregistered during test (for assertions)."""
        return list(self._unregistered)

    @property
    def set_default_history(self) -> list[str]:
        """History of set_default calls (for assertions)."""
        return list(self._set_defaults)
