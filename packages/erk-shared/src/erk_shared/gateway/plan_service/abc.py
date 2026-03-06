"""Domain service ABC for plan operations (no TUI type dependencies)."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.types import PRCheckRun, PRReviewThread


class PlanService(ABC):
    """Abstract base class for plan domain operations.

    Contains operations that are independent of TUI display concerns:
    closing plans, dispatching, fetching content, and GitHub PR data.
    No TUI type imports (PlanRowData, FetchTimings, PlanFilters, BranchActivity).
    """

    @property
    @abstractmethod
    def repo_root(self) -> Path:
        """Get the repository root path."""
        ...

    @property
    @abstractmethod
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        ...

    @property
    @abstractmethod
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs."""
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
    def dispatch_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Dispatch a plan to the implementation queue.

        Args:
            plan_id: The plan ID to dispatch
            plan_url: The plan URL for repository context
        """
        ...

    @abstractmethod
    def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
        """Return plan content from the PR body.

        Args:
            plan_id: The GitHub PR number
            plan_body: The extracted plan content from the PR body

        Returns:
            The plan content, or None if empty
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
    def get_branch_stack(self, branch: str) -> list[str] | None:
        """Get the Graphite stack containing a branch.

        Args:
            branch: The branch name to look up

        Returns:
            Ordered list of branch names in the stack, or None
        """
        ...

    @abstractmethod
    def fetch_check_runs(self, pr_number: int) -> list[PRCheckRun]:
        """Fetch failing check runs for a pull request.

        Args:
            pr_number: The PR number to fetch check runs for

        Returns:
            List of PRCheckRun for failing checks, sorted by name
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

    @abstractmethod
    def fetch_ci_summaries(self, pr_number: int) -> dict[str, str]:
        """Fetch CI failure summaries for a pull request.

        Args:
            pr_number: The PR number to fetch summaries for

        Returns:
            Mapping of check name to summary text. Empty dict if no
            summaries are available.
        """
        ...
