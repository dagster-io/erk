"""Fake plan data provider for testing TUI components."""

from pathlib import Path

from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.browser.fake import FakeBrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.clipboard.fake import FakeClipboard


class FakePlanDataProvider(PlanDataProvider):
    """Fake implementation of PlanDataProvider for testing.

    Returns canned data without making any API calls.
    """

    def __init__(
        self,
        *,
        plans: list[PlanRowData] | None = None,
        clipboard: Clipboard | None = None,
        browser: BrowserLauncher | None = None,
        repo_root: Path | None = None,
        fetch_error: str | None = None,
    ) -> None:
        """Initialize with optional canned plan data.

        Args:
            plans: List of PlanRowData to return, or None for empty list
            clipboard: Clipboard interface, defaults to FakeClipboard()
            browser: BrowserLauncher interface, defaults to FakeBrowserLauncher()
            repo_root: Repository root path, defaults to Path("/fake/repo")
            fetch_error: If set, fetch_plans() raises RuntimeError with this message.
                Use to simulate API failures.
        """
        self._plans = plans or []
        self._fetch_count = 0
        self._clipboard = clipboard if clipboard is not None else FakeClipboard()
        self._browser = browser if browser is not None else FakeBrowserLauncher()
        self._repo_root = repo_root if repo_root is not None else Path("/fake/repo")
        self._fetch_error = fetch_error

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

    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Return canned plan data.

        Args:
            filters: Ignored in fake - returns all canned data

        Returns:
            List of canned PlanRowData

        Raises:
            RuntimeError: If fetch_error is set
        """
        self._fetch_count += 1
        if self._fetch_error is not None:
            raise RuntimeError(self._fetch_error)
        return self._plans

    @property
    def fetch_count(self) -> int:
        """Number of times fetch_plans was called."""
        return self._fetch_count

    def set_plans(self, plans: list[PlanRowData]) -> None:
        """Update the canned plan data.

        Args:
            plans: New list of PlanRowData to return
        """
        self._plans = plans

    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Fake close plan implementation.

        Removes the plan from the internal list and tracks the closure.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL (unused in fake)

        Returns:
            Empty list (no PRs closed in fake)
        """
        self._plans = [p for p in self._plans if p.issue_number != issue_number]
        return []

    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Fake submit to queue implementation.

        Tracks the submission without actually submitting.

        Args:
            issue_number: The issue number to submit
            issue_url: The issue URL (unused in fake)
        """
        # Just track the call - actual submit is complex and not needed for UI tests
        pass

    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fake branch activity implementation.

        Returns empty activity for all plans.

        Args:
            rows: List of plan rows (unused in fake)

        Returns:
            Empty dict - no activity in fake implementation
        """
        return {}


def make_plan_row(
    issue_number: int,
    title: str = "Test Plan",
    *,
    issue_url: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    pr_title: str | None = None,
    pr_state: str | None = None,
    pr_display: str | None = None,
    worktree_name: str = "",
    worktree_branch: str | None = None,
    exists_locally: bool = False,
    run_url: str | None = None,
    run_id: str | None = None,
    run_status: str | None = None,
    run_conclusion: str | None = None,
) -> PlanRowData:
    """Create a PlanRowData for testing with sensible defaults.

    Args:
        issue_number: GitHub issue number
        title: Plan title
        issue_url: URL to the issue (defaults to GitHub URL pattern)
        pr_number: PR number if linked
        pr_url: URL to PR
        pr_title: PR title
        pr_state: PR state (e.g., "OPEN", "MERGED")
        pr_display: Custom PR display string (overrides default "#N" format)
        worktree_name: Local worktree name
        worktree_branch: Branch name in worktree
        exists_locally: Whether worktree exists locally
        run_url: URL to the GitHub Actions run
        run_id: Workflow run ID
        run_status: Workflow run status
        run_conclusion: Workflow run conclusion

    Returns:
        PlanRowData populated with test data
    """
    if issue_url is None:
        issue_url = f"https://github.com/test/repo/issues/{issue_number}"

    computed_pr_display = "-"
    if pr_number is not None:
        computed_pr_display = f"#{pr_number}"

    # Allow override of pr_display for testing indicators like 🔗
    final_pr_display = pr_display if pr_display is not None else computed_pr_display

    return PlanRowData(
        issue_number=issue_number,
        issue_url=issue_url,
        title=title,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_display=final_pr_display,
        checks_display="-",
        worktree_name=worktree_name,
        exists_locally=exists_locally,
        local_impl_display="-",
        remote_impl_display="-",
        run_id_display="-",
        run_state_display="-",
        run_url=run_url,
        full_title=title,
        pr_title=pr_title,
        pr_state=pr_state,
        worktree_branch=worktree_branch,
        last_local_impl_at=None,
        last_remote_impl_at=None,
        run_id=run_id,
        run_status=run_status,
        run_conclusion=run_conclusion,
        log_entries=(),
    )
