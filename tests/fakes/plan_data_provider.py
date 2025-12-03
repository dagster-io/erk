"""Fake plan data provider for testing TUI components."""

from erk_shared.integrations.clipboard.abc import Clipboard
from erk_shared.integrations.clipboard.fake import FakeClipboard

from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData


class FakePlanDataProvider(PlanDataProvider):
    """Fake implementation of PlanDataProvider for testing.

    Returns canned data without making any API calls.
    """

    def __init__(
        self,
        plans: list[PlanRowData] | None = None,
        clipboard: Clipboard | None = None,
    ) -> None:
        """Initialize with optional canned plan data.

        Args:
            plans: List of PlanRowData to return, or None for empty list
            clipboard: Clipboard interface, defaults to FakeClipboard()
        """
        self._plans = plans or []
        self._fetch_count = 0
        self._clipboard = clipboard if clipboard is not None else FakeClipboard()

    @property
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        return self._clipboard

    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Return canned plan data.

        Args:
            filters: Ignored in fake - returns all canned data

        Returns:
            List of canned PlanRowData
        """
        self._fetch_count += 1
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


def make_plan_row(
    issue_number: int,
    title: str = "Test Plan",
    *,
    issue_url: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    pr_title: str | None = None,
    pr_state: str | None = None,
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

    pr_display = "-"
    if pr_number is not None:
        pr_display = f"#{pr_number}"

    return PlanRowData(
        issue_number=issue_number,
        issue_url=issue_url,
        title=title,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_display=pr_display,
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
