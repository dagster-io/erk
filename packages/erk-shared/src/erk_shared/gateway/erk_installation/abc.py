"""Abstract base class for ErkInstallation operations.

ErkInstallation provides access to ~/.erk/ installation data such as
version tracking, config, and command history.
"""

from abc import ABC, abstractmethod


class ErkInstallation(ABC):
    """Abstract interface for erk installation operations.

    All implementations (real, fake) must implement this interface.
    This gateway enables testing by avoiding direct Path.home() calls.
    """

    @abstractmethod
    def get_last_seen_version(self) -> str | None:
        """Get the last version user was notified about.

        Returns:
            Version string if tracking file exists, None otherwise
        """
        ...

    @abstractmethod
    def update_last_seen_version(self, version: str) -> None:
        """Update the last seen version tracking file.

        Args:
            version: Version string to record
        """
        ...
