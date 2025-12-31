"""Graphite-compatible stack backend for backward compatibility.

This backend is used when stack_backend=graphite in .erk/config.toml
(which is the default). It returns True for is_stacking_enabled(),
allowing all stack navigation commands to work as before.
"""

from erk_shared.gateway.stack_backend.abc import StackBackend


class GraphiteCompatStackBackend(StackBackend):
    """Stack backend for Graphite-based stacking.

    This is the default backend, used when stack_backend=graphite.
    It enables all stacking operations for backward compatibility.
    """

    def is_stacking_enabled(self) -> bool:
        """Return True - stacking is enabled with Graphite backend."""
        return True
