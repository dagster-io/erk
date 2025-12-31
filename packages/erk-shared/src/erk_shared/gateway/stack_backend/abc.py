"""Abstract base class for stack backend operations.

The StackBackend ABC provides a minimal interface for stack-aware operations.
This allows commands to check whether stacking is enabled before attempting
stack navigation operations.
"""

from abc import ABC, abstractmethod


class StackBackend(ABC):
    """ABC for stack backend operations.

    Implementations:
    - GraphiteCompatStackBackend: Returns True for backward compatibility
    - SimpleStackBackend: Returns False (no stacking)
    - FakeStackBackend: Configurable via constructor for testing
    """

    @abstractmethod
    def is_stacking_enabled(self) -> bool:
        """Check if stacking operations are enabled.

        Returns:
            True if stack navigation (up/down) is available, False otherwise.
        """
        ...
