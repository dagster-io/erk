"""Fake Clipboard implementation for testing.

FakeClipboard is an in-memory implementation that tracks copy() calls
without actual clipboard access, enabling fast and deterministic tests.
"""

from erk_shared.integrations.clipboard.abc import Clipboard


class FakeClipboard(Clipboard):
    """In-memory fake implementation that tracks copy calls.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(self, should_succeed: bool = True) -> None:
        """Create FakeClipboard with configurable success behavior.

        Args:
            should_succeed: Whether copy() should return True or False.
                Defaults to True for most tests.
        """
        self._should_succeed = should_succeed
        self._copy_calls: list[str] = []

    @property
    def copy_calls(self) -> list[str]:
        """Get the list of copy() calls that were made.

        Returns a copy of the list to prevent external mutation.

        This property is for test assertions only.
        """
        return list(self._copy_calls)

    @property
    def last_copied(self) -> str | None:
        """Get the last text that was copied, or None if no copy calls.

        This property is for test assertions only.
        """
        if not self._copy_calls:
            return None
        return self._copy_calls[-1]

    def copy(self, text: str) -> bool:
        """Track copy call and return configured success state.

        Args:
            text: Text that would have been copied to clipboard

        Returns:
            The configured should_succeed value
        """
        self._copy_calls.append(text)
        return self._should_succeed
