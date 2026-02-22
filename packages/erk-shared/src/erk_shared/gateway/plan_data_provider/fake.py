"""Fake plan data provider for testing TUI components."""

from datetime import UTC, datetime
from pathlib import Path

from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.browser.fake import FakeBrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.github.types import PRReviewThread
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider


class FakePlanDataProvider(PlanDataProvider):
    """Fake implementation of PlanDataProvider for testing.

    Returns canned data without making any API calls.
    """

    def __init__(
        self,
        *,
        plans: list[PlanRowData] | None = None,
        plans_by_labels: dict[tuple[str, ...], list[PlanRowData]] | None = None,
        clipboard: Clipboard | None = None,
        browser: BrowserLauncher | None = None,
        repo_root: Path | None = None,
        fetch_error: str | None = None,
    ) -> None:
        """Initialize with optional canned plan data.

        Args:
            plans: List of PlanRowData to return, or None for empty list
            plans_by_labels: Per-label-set responses for testing view switching.
                When set, fetch_plans() checks this first using the filter labels.
            clipboard: Clipboard interface, defaults to FakeClipboard()
            browser: BrowserLauncher interface, defaults to FakeBrowserLauncher()
            repo_root: Repository root path, defaults to Path("/fake/repo")
            fetch_error: If set, fetch_plans() raises RuntimeError with this message.
                Use to simulate API failures.
        """
        self._plans = plans or []
        self._plans_by_labels = plans_by_labels
        self._fetch_count = 0
        self._clipboard = clipboard if clipboard is not None else FakeClipboard()
        self._browser = browser if browser is not None else FakeBrowserLauncher()
        self._repo_root = repo_root if repo_root is not None else Path("/fake/repo")
        self._fetch_error = fetch_error
        self._plan_content_by_plan_id: dict[int, str] = {}
        self._objective_content_by_plan_id: dict[int, str] = {}
        self._review_threads_by_pr: dict[int, list[PRReviewThread]] = {}

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
            filters: Checks plans_by_labels first using filter labels,
                falls back to default plans list.

        Returns:
            List of canned PlanRowData

        Raises:
            RuntimeError: If fetch_error is set
        """
        self._fetch_count += 1
        if self._fetch_error is not None:
            raise RuntimeError(self._fetch_error)
        if self._plans_by_labels is not None and filters.labels in self._plans_by_labels:
            return self._plans_by_labels[filters.labels]
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

    def close_plan(self, plan_id: int, plan_url: str) -> list[int]:
        """Fake close plan implementation.

        Removes the plan from the internal list and tracks the closure.

        Args:
            plan_id: The plan ID to close
            plan_url: The plan URL (unused in fake)

        Returns:
            Empty list (no PRs closed in fake)
        """
        self._plans = [p for p in self._plans if p.plan_id != plan_id]
        return []

    def submit_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Fake submit to queue implementation.

        Tracks the submission without actually submitting.

        Args:
            plan_id: The plan ID to submit
            plan_url: The plan URL (unused in fake)
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

    def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fake plan content fetch implementation.

        Returns the plan_content if configured, otherwise None.

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

        Returns the objective_content if configured, otherwise None.

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

    def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
        """Fake unresolved comments fetch implementation.

        Returns configured review threads for a PR, or empty list.

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


def make_plan_row(
    plan_id: int,
    full_title: str = "Test Plan",
    *,
    plan_url: str | None = None,
    plan_body: str = "",
    pr_number: int | None = None,
    pr_url: str | None = None,
    pr_title: str | None = None,
    pr_state: str | None = None,
    pr_head_branch: str | None = None,
    pr_display: str | None = None,
    worktree_name: str = "",
    worktree_branch: str | None = None,
    exists_locally: bool = False,
    run_url: str | None = None,
    run_id: str | None = None,
    run_status: str | None = None,
    run_conclusion: str | None = None,
    comment_counts: tuple[int, int] | None = None,
    learn_status: str | None = None,
    learn_plan_issue: int | None = None,
    learn_plan_issue_closed: bool | None = None,
    learn_plan_pr: int | None = None,
    learn_run_url: str | None = None,
    objective_issue: int | None = None,
    objective_done_nodes: int = 0,
    objective_total_nodes: int = 0,
    objective_progress_display: str = "-",
    objective_next_node_display: str = "-",
    objective_deps_display: str = "-",
    objective_in_flight_display: str = "-",
    updated_at: datetime | None = None,
    updated_display: str = "-",
    created_at: datetime | None = None,
    author: str = "test-user",
    is_learn_plan: bool = False,
    lifecycle_display: str = "-",
    status_display: str = "-",
) -> PlanRowData:
    """Create a PlanRowData for testing with sensible defaults.

    Args:
        plan_id: GitHub issue number
        full_title: Full plan title
        plan_url: URL to the issue (defaults to GitHub URL pattern)
        plan_body: Raw issue body text (markdown)
        pr_number: PR number if linked
        pr_url: URL to PR
        pr_title: PR title
        pr_state: PR state (e.g., "OPEN", "MERGED")
        pr_head_branch: Head branch from PR metadata (for landing)
        pr_display: Custom PR display string (overrides default "#N" format)
        worktree_name: Local worktree name
        worktree_branch: Branch name in worktree
        exists_locally: Whether worktree exists locally
        run_url: URL to the GitHub Actions run
        run_id: Workflow run ID
        run_status: Workflow run status
        run_conclusion: Workflow run conclusion
        comment_counts: Tuple of (resolved, total) comment counts (None shows "-")
        learn_status: Learn workflow status ("pending", "completed_with_plan", etc.)
        learn_plan_issue: Issue number of generated learn plan
        learn_plan_issue_closed: Whether the learn plan issue is closed (True/False/None)
        learn_plan_pr: PR number that implemented the learn plan
        learn_run_url: URL to GitHub Actions workflow run (for pending status)
        objective_issue: Objective issue number (for linking plans to objectives)
        objective_done_nodes: Count of done nodes in objective roadmap
        objective_total_nodes: Total nodes in objective roadmap
        objective_progress_display: Progress display (e.g., "3/7" or "-")
        objective_next_node_display: Next pending node display (e.g., "1.3 Add tests" or "-")
        updated_at: Last update datetime (defaults to same as created_at)
        updated_display: Formatted relative time for last update
        created_at: Creation datetime (defaults to 2025-01-01T00:00:00Z)

    Returns:
        PlanRowData populated with test data
    """
    if plan_url is None:
        plan_url = f"https://github.com/test/repo/issues/{plan_id}"

    # Compute learn_display (full text) and learn_display_icon (icon-only)
    if learn_status is None or learn_status == "not_started":
        learn_display = "- not started"
        learn_display_icon = "-"
    elif learn_status == "pending":
        learn_display = "⟳ in progress"
        learn_display_icon = "⟳"
    elif learn_status == "completed_no_plan":
        learn_display = "∅ no insights"
        learn_display_icon = "∅"
    elif learn_status == "completed_with_plan" and learn_plan_issue is not None:
        if learn_plan_issue_closed is True:
            learn_display = f"✅ #{learn_plan_issue}"
            learn_display_icon = f"✅ #{learn_plan_issue}"
        else:
            learn_display = f"📋 #{learn_plan_issue}"
            learn_display_icon = f"📋 #{learn_plan_issue}"
    elif learn_status == "plan_completed" and learn_plan_pr is not None:
        learn_display = f"✓ #{learn_plan_pr}"
        learn_display_icon = f"✓ #{learn_plan_pr}"
    else:
        learn_display = "- not started"
        learn_display_icon = "-"

    computed_pr_display = "-"
    if pr_number is not None:
        computed_pr_display = f"#{pr_number}"

    # Allow override of pr_display for testing indicators like 🔗
    final_pr_display = pr_display if pr_display is not None else computed_pr_display

    # Compute comment counts display based on pr_number presence
    if pr_number is None:
        resolved_count = 0
        total_count = 0
        comments_display = "-"
    elif comment_counts is None:
        resolved_count = 0
        total_count = 0
        comments_display = "0/0"
    else:
        resolved_count, total_count = comment_counts
        comments_display = f"{resolved_count}/{total_count}"

    # Compute objective display
    objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

    # Default created_at to a fixed sentinel datetime
    effective_created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)
    effective_updated_at = updated_at or effective_created_at
    created_display = "-"

    return PlanRowData(
        plan_id=plan_id,
        plan_url=plan_url,
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
        full_title=full_title,
        plan_body=plan_body,
        pr_title=pr_title,
        pr_state=pr_state,
        pr_head_branch=pr_head_branch,
        worktree_branch=worktree_branch,
        last_local_impl_at=None,
        last_remote_impl_at=None,
        run_id=run_id,
        run_status=run_status,
        run_conclusion=run_conclusion,
        log_entries=(),
        resolved_comment_count=resolved_count,
        total_comment_count=total_count,
        comments_display=comments_display,
        learn_status=learn_status,
        learn_plan_issue=learn_plan_issue,
        learn_plan_issue_closed=learn_plan_issue_closed,
        learn_plan_pr=learn_plan_pr,
        learn_run_url=learn_run_url,
        learn_display=learn_display,
        learn_display_icon=learn_display_icon,
        objective_issue=objective_issue,
        objective_display=objective_display,
        objective_done_nodes=objective_done_nodes,
        objective_total_nodes=objective_total_nodes,
        objective_progress_display=objective_progress_display,
        objective_next_node_display=objective_next_node_display,
        objective_deps_display=objective_deps_display,
        objective_in_flight_display=objective_in_flight_display,
        updated_at=effective_updated_at,
        updated_display=updated_display,
        created_at=effective_created_at,
        created_display=created_display,
        author=author,
        is_learn_plan=is_learn_plan,
        lifecycle_display=lifecycle_display,
        status_display=status_display,
    )
