"""Domain service ABC for PR operations (no TUI type dependencies)."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.types import PRCheckRun, PRReviewThread


class PrService(ABC):
    """Abstract base class for PR domain operations.

    Contains operations that are independent of TUI display concerns:
    closing PRs, dispatching, fetching content, and GitHub PR data.
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
    def close_pr(self, pr_number: int, pr_url: str) -> list[int]:
        """Close a PR and its linked PRs.

        Args:
            pr_number: The PR number to close
            pr_url: The PR URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        ...

    @abstractmethod
    def dispatch_to_queue(self, pr_number: int, pr_url: str) -> None:
        """Dispatch a PR to the implementation queue.

        Args:
            pr_number: The PR number to dispatch
            pr_url: The PR URL for repository context
        """
        ...

    @abstractmethod
    def fetch_pr_content(self, pr_number: int, pr_body: str) -> str | None:
        """Return PR content from the PR body.

        Args:
            pr_number: The GitHub PR number
            pr_body: The extracted PR content from the PR body

        Returns:
            The PR content, or None if empty
        """
        ...

    @abstractmethod
    def fetch_objective_content(self, pr_number: int, pr_body: str) -> str | None:
        """Fetch objective content from the first comment of an issue.

        Args:
            pr_number: The GitHub issue number
            pr_body: The issue body (to extract objective_comment_id from metadata)

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
    def fetch_ci_summaries(self, pr_number: int, *, comment_id: int | None) -> dict[str, str]:
        """Fetch CI failure summaries for a pull request.

        If comment_id is provided, fetches the comment directly (1 API call).
        Otherwise falls back to the 4-call path: get PR → find run → find
        ci-summarize job → fetch logs.

        Args:
            pr_number: The PR number to fetch summaries for
            comment_id: Optional GitHub comment ID containing CI summaries

        Returns:
            Mapping of check name to summary text. Empty dict if no
            summaries are available.
        """
        ...
