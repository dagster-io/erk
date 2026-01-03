"""Production implementation of ErkInstallation operations."""

from pathlib import Path

from erk_shared.gateway.erk_installation.abc import ErkInstallation


class RealErkInstallation(ErkInstallation):
    """Production implementation using real filesystem.

    Accesses ~/.erk/ for installation data like version tracking.
    """

    def _installation_path(self) -> Path:
        """Get the erk installation directory.

        Returns:
            Path to ~/.erk/
        """
        return Path.home() / ".erk"

    def get_last_seen_version(self) -> str | None:
        """Get the last version user was notified about.

        Returns:
            Version string if tracking file exists, None otherwise
        """
        path = self._installation_path() / "last_seen_version"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()

    def update_last_seen_version(self, version: str) -> None:
        """Update the last seen version tracking file.

        Args:
            version: Version string to record
        """
        path = self._installation_path() / "last_seen_version"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(version, encoding="utf-8")
