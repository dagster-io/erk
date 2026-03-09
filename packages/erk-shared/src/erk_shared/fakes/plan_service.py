"""Fake plan service for testing."""

from pathlib import Path

from erk_shared.fakes.browser import FakeBrowserLauncher
from erk_shared.fakes.clipboard import FakeClipboard
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.types import PRCheckRun, PRReviewThread
from erk_shared.gateway.plan_service.abc import PlanService


class FakePlanService(PlanService):
    """Fake implementation of PlanService for testing.

    Returns canned data without making any API calls.
    """

    def __init__(
        self,
        *,
        clipboard: Clipboard | None = None,
        browser: BrowserLauncher | None = None,
        repo_root: Path | None = None,
    ) -> None:
        """Initialize with optional canned data.

        Args:
            clipboard: Clipboard interface, defaults to FakeClipboard()
            browser: BrowserLauncher interface, defaults to FakeBrowserLauncher()
            repo_root: Repository root path, defaults to Path("/fake/repo")
        """
        self._clipboard = clipboard if clipboard is not None else FakeClipboard()
        self._browser = browser if browser is not None else FakeBrowserLauncher()
        self._repo_root = repo_root if repo_root is not None else Path("/fake/repo")
        self._plan_content_by_plan_id: dict[int, str] = {}
        self._objective_content_by_plan_id: dict[int, str] = {}
        self._review_threads_by_pr: dict[int, list[PRReviewThread]] = {}
        self._check_runs_by_pr: dict[int, list[PRCheckRun]] = {}
        self._ci_summaries_by_pr: dict[int, dict[str, str]] = {}
        self._stacks_by_branch: dict[str, list[str]] = {}

    @property
    def repo_root(self) -> Path:
        """Get the repository root path."""
        return self._repo_root

    @property
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        return self._clipboard

    @property
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs."""
        return self._browser

    def close_plan(self, plan_id: int, plan_url: str) -> list[int]:
        """Fake close plan implementation.

        Args:
            plan_id: The plan ID to close
            plan_url: The plan URL (unused in fake)

        Returns:
            Empty list (no PRs closed in fake)
        """
        return []

    def dispatch_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Fake dispatch to queue implementation.

        Args:
            plan_id: The plan ID to dispatch
            plan_url: The plan URL (unused in fake)
        """

    def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fake plan content fetch implementation.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (unused in fake)

        Returns:
            The configured plan content for this plan, or None
        """
        return self._plan_content_by_plan_id.get(plan_id)

    def set_plan_content(self, plan_id: int, content: str) -> None:
        """Set the plan content to return for a specific plan.

        Args:
            plan_id: The GitHub issue number
            content: The plan content to return
        """
        self._plan_content_by_plan_id[plan_id] = content

    def fetch_objective_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fake objective content fetch implementation.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (unused in fake)

        Returns:
            The configured objective content for this plan, or None
        """
        return self._objective_content_by_plan_id.get(plan_id)

    def set_objective_content(self, plan_id: int, content: str) -> None:
        """Set the objective content to return for a specific plan.

        Args:
            plan_id: The GitHub issue number
            content: The objective content to return
        """
        self._objective_content_by_plan_id[plan_id] = content

    def get_branch_stack(self, branch: str) -> list[str] | None:
        """Fake branch stack lookup.

        Args:
            branch: The branch name to look up

        Returns:
            Configured list of branch names, or None
        """
        return self._stacks_by_branch.get(branch)

    def set_branch_stack(self, branch: str, stack: list[str]) -> None:
        """Configure the stack to return for a branch.

        Args:
            branch: The branch name
            stack: List of branch names in the stack
        """
        self._stacks_by_branch[branch] = stack

    def fetch_check_runs(self, pr_number: int) -> list[PRCheckRun]:
        """Fake check runs fetch implementation.

        Args:
            pr_number: The PR number to fetch check runs for

        Returns:
            Configured list of PRCheckRun for this PR, or empty list
        """
        return self._check_runs_by_pr.get(pr_number, [])

    def set_check_runs(self, pr_number: int, check_runs: list[PRCheckRun]) -> None:
        """Set the check runs to return for a specific PR.

        Args:
            pr_number: The PR number
            check_runs: List of PRCheckRun to return
        """
        self._check_runs_by_pr[pr_number] = check_runs

    def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
        """Fake unresolved comments fetch implementation.

        Args:
            pr_number: The PR number to fetch threads for

        Returns:
            Configured list of PRReviewThread for this PR, or empty list
        """
        return self._review_threads_by_pr.get(pr_number, [])

    def set_review_threads(self, pr_number: int, threads: list[PRReviewThread]) -> None:
        """Set the review threads to return for a specific PR.

        Args:
            pr_number: The PR number
            threads: List of PRReviewThread to return
        """
        self._review_threads_by_pr[pr_number] = threads

    def fetch_ci_summaries(self, pr_number: int, *, comment_id: int | None) -> dict[str, str]:
        """Fake CI summaries fetch implementation.

        Args:
            pr_number: The PR number to fetch summaries for
            comment_id: Optional GitHub comment ID (unused in fake)

        Returns:
            Configured mapping of check name to summary text, or empty dict
        """
        return self._ci_summaries_by_pr.get(pr_number, {})

    def set_ci_summaries(self, pr_number: int, summaries: dict[str, str]) -> None:
        """Set the CI summaries to return for a specific PR.

        Args:
            pr_number: The PR number
            summaries: Mapping of check name to summary text
        """
        self._ci_summaries_by_pr[pr_number] = summaries
