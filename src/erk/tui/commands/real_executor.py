"""Real implementation of CommandExecutor for production use."""

from collections.abc import Callable
from typing import Any

from erk.tui.commands.executor import CommandExecutor


class RealCommandExecutor(CommandExecutor):
    """Production executor using injected dependencies.

    Uses callables for each operation to decouple from concrete implementations.
    """

    def __init__(
        self,
        browser_launch: Callable[[str], Any],
        clipboard_copy: Callable[[str], Any],
        close_plan_fn: Callable[[int, str], list[int]],
        notify_fn: Callable[[str], None],
        refresh_fn: Callable[[], None],
        submit_to_queue_fn: Callable[[int, str], None],
    ) -> None:
        """Initialize with dependency functions.

        Args:
            browser_launch: Function to launch URL in browser (return value ignored)
            clipboard_copy: Function to copy text to clipboard (return value ignored)
            close_plan_fn: Function to close plan and linked PRs
            notify_fn: Function to show notification
            refresh_fn: Function to trigger data refresh
            submit_to_queue_fn: Function to submit plan to implementation queue
        """
        self._browser_launch = browser_launch
        self._clipboard_copy = clipboard_copy
        self._close_plan_fn = close_plan_fn
        self._notify_fn = notify_fn
        self._refresh_fn = refresh_fn
        self._submit_to_queue_fn = submit_to_queue_fn

    def open_url(self, url: str) -> None:
        """Open URL in browser."""
        self._browser_launch(url)

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        self._clipboard_copy(text)

    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close plan and linked PRs."""
        return self._close_plan_fn(issue_number, issue_url)

    def notify(self, message: str) -> None:
        """Show notification to user."""
        self._notify_fn(message)

    def refresh_data(self) -> None:
        """Trigger data refresh."""
        self._refresh_fn()

    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit plan to implementation queue."""
        self._submit_to_queue_fn(issue_number, issue_url)
