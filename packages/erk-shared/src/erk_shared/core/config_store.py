"""Global configuration store abstraction - ABC only.

This module provides the abstract interface for global config operations.
The real implementation (RealConfigStore) remains in erk.core.config_store.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.context.types import GlobalConfig


class ConfigStore(ABC):
    """Abstract interface for global config operations.

    Provides dependency injection for global config access, enabling
    in-memory implementations for tests without touching filesystem.
    """

    @abstractmethod
    def exists(self) -> bool:
        """Check if global config exists."""
        ...

    @abstractmethod
    def load(self) -> GlobalConfig:
        """Load global config.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        ...

    @abstractmethod
    def save(self, config: GlobalConfig) -> None:
        """Save global config.

        Args:
            config: GlobalConfig instance to save
        """
        ...

    @abstractmethod
    def path(self) -> Path:
        """Get the path to the global config file.

        Returns:
            Path to config file (for error messages and debugging)
        """
        ...
