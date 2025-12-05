"""Fake command executor for testing TUI command palette."""

from erk.tui.commands.executor import CommandExecutor


class FakeCommandExecutor(CommandExecutor):
    """In-memory fake for testing command execution.

    Tracks all operations performed for assertion in tests.
    """

    def __init__(self) -> None:
        """Initialize with empty tracking state."""
        self._opened_urls: list[str] = []
        self._copied_texts: list[str] = []
        self._closed_plans: list[tuple[int, str]] = []
        self._notifications: list[str] = []
        self._refresh_count: int = 0
        self._close_plan_return: list[int] = []
        self._submitted_to_queue: list[tuple[int, str]] = []

    @property
    def opened_urls(self) -> list[str]:
        """URLs that were opened in browser."""
        return list(self._opened_urls)

    @property
    def copied_texts(self) -> list[str]:
        """Texts that were copied to clipboard."""
        return list(self._copied_texts)

    @property
    def closed_plans(self) -> list[tuple[int, str]]:
        """Plans that were closed (issue_number, issue_url)."""
        return list(self._closed_plans)

    @property
    def notifications(self) -> list[str]:
        """Notifications that were shown."""
        return list(self._notifications)

    @property
    def refresh_count(self) -> int:
        """Number of times refresh was triggered."""
        return self._refresh_count

    @property
    def submitted_to_queue(self) -> list[tuple[int, str]]:
        """Plans that were submitted to queue (issue_number, issue_url)."""
        return list(self._submitted_to_queue)

    def set_close_plan_return(self, pr_numbers: list[int]) -> None:
        """Configure what close_plan should return.

        Args:
            pr_numbers: List of PR numbers to return when close_plan is called
        """
        self._close_plan_return = pr_numbers

    def open_url(self, url: str) -> None:
        """Track URL open."""
        self._opened_urls.append(url)

    def copy_to_clipboard(self, text: str) -> None:
        """Track clipboard copy."""
        self._copied_texts.append(text)

    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Track plan close and return configured PRs."""
        self._closed_plans.append((issue_number, issue_url))
        return self._close_plan_return

    def notify(self, message: str) -> None:
        """Track notification."""
        self._notifications.append(message)

    def refresh_data(self) -> None:
        """Track refresh."""
        self._refresh_count += 1

    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Track queue submission."""
        self._submitted_to_queue.append((issue_number, issue_url))
