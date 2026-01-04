"""ErkInstallation gateway ABC.

This module defines the abstract interface for all ~/.erk/ filesystem operations.
Consolidates ConfigStore and command history path access into a single gateway.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.context.types import GlobalConfig


class ErkInstallation(ABC):
    """Abstract interface for ~/.erk/ filesystem operations.

    Provides dependency injection for global installation access, enabling
    in-memory implementations for tests without touching filesystem.
    """

    # --- Config operations (migrated from ConfigStore) ---

    @abstractmethod
    def config_exists(self) -> bool:
        """Check if global config file exists."""
        ...

    @abstractmethod
    def load_config(self) -> GlobalConfig:
        """Load global config from ~/.erk/config.toml.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        ...

    @abstractmethod
    def save_config(self, config: GlobalConfig) -> None:
        """Save global config to ~/.erk/config.toml.

        Args:
            config: GlobalConfig instance to save

        Raises:
            PermissionError: If directory or file cannot be written
        """
        ...

    @abstractmethod
    def config_path(self) -> Path:
        """Get path to config file (for error messages).

        Returns:
            Path to ~/.erk/config.toml
        """
        ...

    # --- Command history operations ---

    @abstractmethod
    def get_command_log_path(self) -> Path:
        """Get path to command history log file.

        Returns:
            Path to ~/.erk/command_history.jsonl
        """
        ...

    # --- Planner registry operations ---

    @abstractmethod
    def get_planners_config_path(self) -> Path:
        """Get path to planners configuration file.

        Returns:
            Path to ~/.erk/planners.toml
        """
        ...

    # --- Root path access ---

    @abstractmethod
    def root(self) -> Path:
        """Get the root path of the erk installation (~/.erk/).

        This enables derived path computation for callers that need to construct
        paths within the installation directory without hardcoding Path.home().

        Returns:
            Path to ~/.erk/ (or equivalent in fake implementations)
        """
        ...

    # --- Version tracking operations ---

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
