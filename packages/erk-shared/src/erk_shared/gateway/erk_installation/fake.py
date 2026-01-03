"""Fake ErkInstallation for testing.

FakeErkInstallation is an in-memory implementation that accepts pre-configured
state in its constructor. No filesystem access occurs.
"""

from erk_shared.gateway.erk_installation.abc import ErkInstallation


class FakeErkInstallation(ErkInstallation):
    """In-memory fake implementation of ErkInstallation.

    This class has NO public setup methods. All state is provided via
    constructor. Uses mutable state since fakes are test infrastructure.
    """

    def __init__(
        self,
        *,
        last_seen_version: str | None = None,
    ) -> None:
        """Create FakeErkInstallation with pre-configured state.

        Args:
            last_seen_version: Pre-configured last seen version (None means no file exists)
        """
        self._last_seen_version = last_seen_version
        self._version_updates: list[str] = []

    def get_last_seen_version(self) -> str | None:
        """Get the last version user was notified about.

        Returns:
            Version string if set, None otherwise
        """
        return self._last_seen_version

    def update_last_seen_version(self, version: str) -> None:
        """Update the last seen version.

        Tracks updates for test assertions.

        Args:
            version: Version string to record
        """
        self._last_seen_version = version
        self._version_updates.append(version)

    @property
    def version_updates(self) -> list[str]:
        """Get the list of version updates that were made.

        Returns a copy to prevent accidental mutation by tests.

        This property is for test assertions only.
        """
        return self._version_updates.copy()
