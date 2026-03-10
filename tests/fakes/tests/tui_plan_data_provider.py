"""Fake plan data provider for testing TUI components."""

from datetime import UTC, datetime

from erk.tui.data.provider_abc import PrDataProvider
from erk.tui.data.types import FetchTimings, PrFilters, PrRowData, RunRowData
from erk.tui.sorting.types import BranchActivity


class FakePrDataProvider(PrDataProvider):
    """Fake implementation of PrDataProvider for testing.

    Returns canned data without making any API calls.
    Only handles TUI data assembly methods (fetch_prs, etc.).
    Domain operations (close_pr, dispatch, etc.) are on FakePrService.
    """

    def __init__(
        self,
        *,
        plans: list[PrRowData] | None = None,
        plans_by_labels: dict[tuple[str, ...], list[PrRowData]] | None = None,
        fetch_error: str | None = None,
    ) -> None:
        """Initialize with optional canned plan data.

        Args:
            plans: List of PrRowData to return, or None for empty list
            plans_by_labels: Per-label-set responses for testing view switching.
                When set, fetch_prs() checks this first using the filter labels.
            fetch_error: If set, fetch_prs() raises RuntimeError with this message.
                Use to simulate API failures.
        """
        self._plans = plans or []
        self._plans_by_labels = plans_by_labels
        self._fetch_count = 0
        self._fetch_error = fetch_error
        self._runs: list[RunRowData] = []

    def fetch_prs(self, filters: PrFilters) -> tuple[list[PrRowData], FetchTimings | None]:
        """Return canned plan data.

        Args:
            filters: Checks plans_by_labels first using filter labels,
                falls back to default plans list.

        Returns:
            Tuple of (list of canned PrRowData, None timings)

        Raises:
            RuntimeError: If fetch_error is set
        """
        self._fetch_count += 1
        if self._fetch_error is not None:
            raise RuntimeError(self._fetch_error)
        if self._plans_by_labels is not None and filters.labels in self._plans_by_labels:
            return (self._plans_by_labels[filters.labels], None)
        return (self._plans, None)

    @property
    def fetch_count(self) -> int:
        """Number of times fetch_prs was called."""
        return self._fetch_count

    def set_plans(self, plans: list[PrRowData]) -> None:
        """Update the canned plan data.

        Args:
            plans: New list of PrRowData to return
        """
        self._plans = plans

    def fetch_runs(self) -> list[RunRowData]:
        """Return canned run data.

        Returns:
            List of canned RunRowData
        """
        return list(self._runs)

    def set_runs(self, runs: list[RunRowData]) -> None:
        """Update the canned run data.

        Args:
            runs: New list of RunRowData to return
        """
        self._runs = runs

    def fetch_branch_activity(self, rows: list[PrRowData]) -> dict[int, BranchActivity]:
        """Fake branch activity implementation.

        Args:
            rows: List of plan rows (unused in fake)

        Returns:
            Empty dict - no activity in fake implementation
        """
        return {}

    def fetch_prs_by_ids(self, pr_ids: set[int]) -> list[PrRowData]:
        """Fake plans-by-ids fetch implementation.

        Args:
            pr_ids: Set of plan issue numbers to fetch

        Returns:
            List of PrRowData matching the given plan IDs, sorted by pr_number
        """
        return sorted(
            [p for p in self._plans if p.pr_number in pr_ids],
            key=lambda r: r.pr_number,
        )

    def fetch_prs_for_objective(self, objective_issue: int) -> list[PrRowData]:
        """Fake plans-for-objective fetch implementation.

        Args:
            objective_issue: The objective issue number to filter by

        Returns:
            List of PrRowData matching the given objective_issue
        """
        return [p for p in self._plans if p.objective_issue == objective_issue]


def make_pr_row(
    pr_number: int,
    full_title: str = "Test Plan",
    *,
    pr_url: str | None = None,
    pr_body: str = "",
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
    checks_passing: bool | None = None,
    checks_counts: tuple[int, int] | None = None,
    learn_status: str | None = None,
    learn_plan_issue: int | None = None,
    learn_plan_issue_closed: bool | None = None,
    learn_plan_pr: int | None = None,
    learn_run_url: str | None = None,
    objective_issue: int | None = None,
    objective_done_nodes: int = 0,
    objective_total_nodes: int = 0,
    objective_progress_display: str = "-",
    objective_slug_display: str = "-",
    objective_state_display: str = "-",
    objective_deps_display: str = "-",
    objective_deps_plans: tuple[tuple[str, str], ...] = (),
    objective_next_node_display: str = "-",
    updated_at: datetime | None = None,
    updated_display: str = "-",
    created_at: datetime | None = None,
    author: str = "test-user",
    is_learn_plan: bool = False,
    lifecycle_display: str = "-",
    status_display: str = "-",
) -> PrRowData:
    """Create a PrRowData for testing with sensible defaults.

    Args:
        pr_number: GitHub issue/PR number
        full_title: Full title
        pr_url: URL to PR (defaults to GitHub URL pattern)
        pr_body: Raw issue body text (markdown)
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
        checks_passing: Whether checks are passing
        checks_counts: Tuple of (passing, total) check counts
        learn_status: Learn workflow status ("pending", "completed_with_plan", etc.)
        learn_plan_issue: Issue number of generated learn plan
        learn_plan_issue_closed: Whether the learn plan issue is closed (True/False/None)
        learn_plan_pr: PR number that implemented the learn plan
        learn_run_url: URL to GitHub Actions workflow run (for pending status)
        objective_issue: Objective issue number (for linking plans to objectives)
        objective_done_nodes: Count of done nodes in objective roadmap
        objective_total_nodes: Total nodes in objective roadmap
        objective_progress_display: Progress display (e.g., "3/7" or "-")
        objective_slug_display: Slug or stripped title fallback (max 25 chars)
        objective_state_display: Sparkline string (e.g., "done done done wip wip todo")
        objective_deps_display: Dependency status of next node (e.g., "ready", "in progress")
        objective_deps_plans: Blocking dep PR references
        objective_next_node_display: Next node ID display
        updated_at: Last update datetime (defaults to same as created_at)
        updated_display: Formatted relative time for last update
        created_at: Creation datetime (defaults to 2025-01-01T00:00:00Z)
        author: Author username
        is_learn_plan: Whether this is a learn plan
        lifecycle_display: Lifecycle stage display string
        status_display: Status indicators display string

    Returns:
        PrRowData populated with test data
    """
    if pr_url is None:
        pr_url = f"https://github.com/test/repo/issues/{pr_number}"

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

    computed_pr_display = f"#{pr_number}"

    # Allow override of pr_display for testing indicators like link emoji
    final_pr_display = pr_display if pr_display is not None else computed_pr_display

    # Compute comment counts display
    if comment_counts is None:
        resolved_count = 0
        total_count = 0
        comments_display = "0/0"
    else:
        resolved_count, total_count = comment_counts
        comments_display = f"{resolved_count}/{total_count}"

    # Compute objective display
    objective_url = (
        f"https://github.com/test/repo/issues/{objective_issue}"
        if objective_issue is not None
        else None
    )
    objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

    # Default created_at to a fixed sentinel datetime
    effective_created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)
    effective_updated_at = updated_at or effective_created_at
    created_display = "-"

    return PrRowData(
        pr_number=pr_number,
        pr_url=pr_url,
        pr_display=final_pr_display,
        checks_display="-",
        checks_passing=checks_passing,
        checks_counts=checks_counts,
        ci_summary_comment_id=None,
        worktree_name=worktree_name,
        exists_locally=exists_locally,
        local_impl_display="-",
        remote_impl_display="-",
        run_id_display="-",
        run_state_display="-",
        run_url=run_url,
        full_title=full_title,
        pr_body=pr_body,
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
        objective_url=objective_url,
        objective_display=objective_display,
        objective_done_nodes=objective_done_nodes,
        objective_total_nodes=objective_total_nodes,
        objective_progress_display=objective_progress_display,
        objective_slug_display=objective_slug_display,
        objective_state_display=objective_state_display,
        objective_deps_display=objective_deps_display,
        objective_deps_plans=objective_deps_plans,
        objective_next_node_display=objective_next_node_display,
        updated_at=effective_updated_at,
        updated_display=updated_display,
        created_at=effective_created_at,
        created_display=created_display,
        author=author,
        is_learn_plan=is_learn_plan,
        lifecycle_display=lifecycle_display,
        status_display=status_display,
    )


def make_run_row(
    run_id: str,
    *,
    run_url: str | None = None,
    status: str = "completed",
    conclusion: str | None = "success",
    status_display: str = "✅ Success",
    workflow_name: str = "plan-implement",
    pr_number: int | None = None,
    pr_url: str | None = None,
    pr_display: str = "-",
    pr_title: str | None = None,
    pr_state: str | None = None,
    pr_status_display: str = "-",
    title_display: str = "-",
    branch_display: str = "-",
    submitted_display: str = "03-09 14:30",
    created_at: datetime | None = None,
    checks_display: str = "-",
    run_id_display: str | None = None,
    branch: str = "-",
) -> RunRowData:
    """Create a RunRowData for testing with sensible defaults.

    Args:
        run_id: GitHub Actions workflow run ID
        run_url: URL to the GitHub Actions run page
        status: Raw run status
        conclusion: Raw run conclusion
        status_display: Pre-formatted status string
        workflow_name: Workflow command name
        pr_number: Linked PR number
        pr_url: URL to the linked PR
        pr_display: Formatted PR cell content
        pr_title: PR title
        pr_state: PR state ("OPEN", "MERGED", "CLOSED", or None)
        pr_status_display: Pre-formatted PR status emoji (e.g., "👀", "-")
        title_display: Truncated title for display
        branch_display: Branch name for display
        submitted_display: Formatted submission time
        created_at: UTC datetime when run was created
        checks_display: Formatted checks cell content
        run_id_display: Formatted run ID for display

    Returns:
        RunRowData populated with test data
    """
    if run_url is None:
        run_url = f"https://github.com/test/repo/actions/runs/{run_id}"
    effective_created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)
    effective_run_id_display = run_id_display if run_id_display is not None else run_id

    return RunRowData(
        run_id=run_id,
        run_url=run_url,
        status=status,
        conclusion=conclusion,
        status_display=status_display,
        workflow_name=workflow_name,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_display=pr_display,
        pr_title=pr_title,
        pr_state=pr_state,
        pr_status_display=pr_status_display,
        title_display=title_display,
        branch_display=branch_display,
        submitted_display=submitted_display,
        created_at=effective_created_at,
        checks_display=checks_display,
        run_id_display=effective_run_id_display,
        branch=branch,
    )
