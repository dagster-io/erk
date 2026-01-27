"""Data provider ABC for TUI plan table."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard


class PlanDataProvider(ABC):
    """Abstract base class for plan data providers.

    Defines the interface for fetching plan data for TUI display.
    """

    @property
    @abstractmethod
    def repo_root(self) -> Path:
        """Get the repository root path.

        Returns:
            Path to the repository root directory
        """
        ...

    @property
    @abstractmethod
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations.

        Returns:
            Clipboard interface for copying to system clipboard
        """
        ...

    @property
    @abstractmethod
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs.

        Returns:
            BrowserLauncher interface for opening URLs in browser
        """
        ...

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Fetch plans matching the given filters.

        Args:
            filters: Filter options for the query

        Returns:
            List of PlanRowData objects for display
        """
        ...

    @abstractmethod
    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close a plan and its linked PRs.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        ...

    @abstractmethod
    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit a plan to the implementation queue.

        Args:
            issue_number: The issue number to submit
            issue_url: The issue URL for repository context
        """
        ...

    @abstractmethod
    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Examines commits on each local branch (not in trunk) to determine
        the most recent activity.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of issue_number to BranchActivity for plans with local worktrees.
            Plans without local worktrees are not included in the result.
        """
        ...

    @abstractmethod
    def fetch_plan_content(self, issue_number: int, issue_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue.

        Args:
            issue_number: The GitHub issue number
            issue_body: The issue body (to extract plan_comment_id from metadata)

        Returns:
            The extracted plan content, or None if not found
        """
        ...
