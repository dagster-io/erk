"""Abstract interface for executing palette commands."""

from abc import ABC, abstractmethod


class CommandExecutor(ABC):
    """Abstract interface for executing palette commands.

    This ABC defines the operations that commands can perform.
    Real and fake implementations handle the actual execution.
    """

    @abstractmethod
    def open_url(self, url: str) -> None:
        """Open URL in browser.

        Args:
            url: The URL to open
        """
        ...

    @abstractmethod
    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard.

        Args:
            text: The text to copy
        """
        ...

    @abstractmethod
    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close plan and linked PRs.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        ...

    @abstractmethod
    def notify(self, message: str) -> None:
        """Show notification to user.

        Args:
            message: The message to display
        """
        ...

    @abstractmethod
    def refresh_data(self) -> None:
        """Trigger data refresh."""
        ...

    @abstractmethod
    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit plan to queue for remote AI implementation.

        Args:
            issue_number: The issue number to submit
            issue_url: The issue URL for repository context
        """
        ...
