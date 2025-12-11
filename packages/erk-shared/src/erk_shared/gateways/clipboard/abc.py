"""Clipboard operations abstraction for testing.

This module provides an ABC for clipboard operations to enable
testing without actual clipboard access and to gracefully handle
headless/SSH environments.
"""

from abc import ABC, abstractmethod


class Clipboard(ABC):
    """Abstract clipboard operations for dependency injection."""

    @abstractmethod
    def copy(self, text: str) -> bool:
        """Copy text to clipboard.

        Args:
            text: Text to copy to clipboard

        Returns:
            True if copy succeeded, False if clipboard unavailable
        """
        ...
