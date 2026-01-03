"""Abstract base class for Claude settings file operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class ClaudeSettingsStore(ABC):
    """Abstract interface for Claude settings file operations.

    This gateway provides access to Claude settings files, primarily the global
    settings at ~/.claude/settings.json. The gateway pattern ensures tests use
    FakeClaudeSettingsStore which never accesses the real home directory.

    Two implementations:
    - RealClaudeSettingsStore: Production - reads/writes real filesystem
    - FakeClaudeSettingsStore: Testing - in-memory storage, never touches disk
    """

    @abstractmethod
    def get_global_settings_path(self) -> Path:
        """Get path to global Claude settings (~/.claude/settings.json).

        Returns:
            Path to the global settings file.
            - Real: Returns Path.home() / ".claude" / "settings.json"
            - Fake: Returns a configurable fake path (never real home dir)
        """
        ...

    @abstractmethod
    def read(self, path: Path) -> dict | None:
        """Read settings from path.

        Args:
            path: Path to settings.json file

        Returns:
            Parsed settings dict, or None if file doesn't exist

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            OSError: If file cannot be read
        """
        ...

    @abstractmethod
    def write(self, path: Path, settings: dict) -> Path | None:
        """Write settings to path.

        Creates a backup of the existing file before writing (if it exists).

        Args:
            path: Path to settings.json file
            settings: Settings dict to write

        Returns:
            Path to backup file if created, None if no backup was needed
            (file didn't exist).

        Raises:
            PermissionError: If unable to write to file
            OSError: If unable to write to file
        """
        ...
