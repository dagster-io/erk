"""Data provider ABC for TUI plan table."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.types import PRReviewThread


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
    def close_plan(self, plan_id: int, plan_url: str) -> list[int]:
        """Close a plan and its linked PRs.

        Args:
            plan_id: The plan ID to close
            plan_url: The plan URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        ...

    @abstractmethod
    def submit_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Submit a plan to the implementation queue.

        Args:
            plan_id: The plan ID to submit
            plan_url: The plan URL for repository context
        """
        ...

    @abstractmethod
    def update_objective_after_land(
        self,
        *,
        objective_issue: int,
        pr_num: int,
        branch: str,
    ) -> None:
        """Update an objective after landing a PR.

        Args:
            objective_issue: The objective issue number to update
            pr_num: The PR number that was landed
            branch: The PR head branch name
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
            Mapping of plan_id to BranchActivity for plans with local worktrees.
            Plans without local worktrees are not included in the result.
        """
        ...

    @abstractmethod
    def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (to extract plan_comment_id from metadata)

        Returns:
            The extracted plan content, or None if not found
        """
        ...

    @abstractmethod
    def fetch_objective_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fetch objective content from the first comment of an issue.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (to extract objective_comment_id from metadata)

        Returns:
            The extracted objective content, or None if not found
        """
        ...

    @abstractmethod
    def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
        """Fetch unresolved review threads for a pull request.

        Args:
            pr_number: The PR number to fetch threads for

        Returns:
            List of unresolved PRReviewThread objects sorted by (path, line)
        """
        ...
