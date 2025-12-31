"""Simple stack backend that disables stacking operations.

This backend is used when stack_backend=simple in .erk/config.toml.
It returns False for is_stacking_enabled(), causing stack navigation
commands (up, down) to show helpful error messages.
"""

from erk_shared.gateway.stack_backend.abc import StackBackend


class SimpleStackBackend(StackBackend):
    """Stack backend that disables stacking.

    Used when the user configures stack_backend=simple in their .erk/config.toml.
    All stacking operations will be disabled.
    """

    def is_stacking_enabled(self) -> bool:
        """Return False - stacking is disabled in simple mode."""
        return False
