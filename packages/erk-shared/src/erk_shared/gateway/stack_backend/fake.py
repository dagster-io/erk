"""Fake stack backend for testing.

This module provides a configurable FakeStackBackend for unit tests.
The stacking_enabled state is configured via the constructor.
"""

from erk_shared.gateway.stack_backend.abc import StackBackend


class FakeStackBackend(StackBackend):
    """Fake stack backend with configurable stacking state.

    Used in tests to simulate different stack backend configurations.

    Args:
        stacking_enabled: Whether stacking should be enabled (default True)
    """

    def __init__(self, *, stacking_enabled: bool) -> None:
        """Initialize with specified stacking state."""
        self._stacking_enabled = stacking_enabled

    def is_stacking_enabled(self) -> bool:
        """Return the configured stacking state."""
        return self._stacking_enabled
