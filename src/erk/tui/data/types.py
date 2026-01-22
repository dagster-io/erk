"""Data types for TUI components."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PlanRowData:
    """Row data for displaying a plan in the TUI table.

    Contains pre-formatted display strings and raw data needed for actions.
    Immutable to ensure table state consistency.

    Attributes:
        issue_number: GitHub issue number (e.g., 123)
        issue_url: Full URL to the GitHub issue
        title: Plan title (truncated for display)
        pr_number: PR number if linked, None otherwise
        pr_url: URL to PR (GitHub or Graphite), None if no PR
        pr_display: Formatted PR cell content (e.g., "#123 👀")
        checks_display: Formatted checks cell (e.g., "✓" or "✗")
        worktree_name: Name of local worktree, empty string if none
        exists_locally: Whether worktree exists on local machine
        local_impl_display: Relative time since last local impl (e.g., "2h ago")
        remote_impl_display: Relative time since last remote impl
        run_id_display: Formatted workflow run ID
        run_state_display: Formatted workflow run state
        run_url: URL to the GitHub Actions run page
        full_title: Complete untruncated plan title
        issue_body: Raw issue body text (markdown)
        pr_title: PR title if linked
        pr_state: PR state (e.g., "OPEN", "MERGED", "CLOSED")
        pr_head_branch: Head branch from PR metadata (source branch for landing)
        worktree_branch: Branch name in the worktree (if exists locally)
        last_local_impl_at: Raw timestamp for local impl
        last_remote_impl_at: Raw timestamp for remote impl
        run_id: Raw workflow run ID (for display and URL construction)
        run_status: Workflow run status (e.g., "completed", "in_progress")
        run_conclusion: Workflow run conclusion (e.g., "success", "failure", "cancelled")
        log_entries: List of (event_name, timestamp, comment_url) for plan log
        resolved_comment_count: Count of resolved PR review comments
        total_comment_count: Total count of PR review comments
        comments_display: Formatted display of comments (e.g., "3/5" or "-")
        learn_status: Raw learn status value from plan header
        learn_plan_issue: Plan issue number (for completed_with_plan status)
        learn_plan_pr: PR number (for plan_completed status)
        learn_run_url: URL to GitHub Actions workflow run (for pending status)
        learn_display: Formatted display string with text (e.g., "- not started", "⟳ in progress")
        learn_display_icon: Icon-only display for table ("-", "⟳", "∅", "#456", "✓ #12")
    """

    issue_number: int
    issue_url: str | None
    title: str
    pr_number: int | None
    pr_url: str | None
    pr_display: str
    checks_display: str
    worktree_name: str
    exists_locally: bool
    local_impl_display: str
    remote_impl_display: str
    run_id_display: str
    run_state_display: str
    run_url: str | None
    full_title: str
    issue_body: str
    pr_title: str | None
    pr_state: str | None
    pr_head_branch: str | None
    worktree_branch: str | None
    last_local_impl_at: datetime | None
    last_remote_impl_at: datetime | None
    run_id: str | None
    run_status: str | None
    run_conclusion: str | None
    log_entries: tuple[tuple[str, str, str], ...]
    resolved_comment_count: int
    total_comment_count: int
    comments_display: str
    learn_status: str | None
    learn_plan_issue: int | None
    learn_plan_pr: int | None
    learn_run_url: str | None
    learn_display: str
    learn_display_icon: str


@dataclass(frozen=True)
class PlanFilters:
    """Filter options for plan list queries.

    Matches options from the existing CLI command for consistency.

    Attributes:
        labels: Labels to filter by (default: ["erk-plan"])
        state: Filter by state ("open", "closed", or None for all)
        run_state: Filter by workflow run state (e.g., "in_progress")
        limit: Maximum number of results (None for no limit)
        show_prs: Whether to include PR data
        show_runs: Whether to include workflow run data
        creator: Filter by creator username (None for all users)
    """

    labels: tuple[str, ...]
    state: str | None
    run_state: str | None
    limit: int | None
    show_prs: bool
    show_runs: bool
    creator: str | None = None

    @staticmethod
    def default() -> PlanFilters:
        """Create default filters (open erk-plan issues)."""
        return PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            creator=None,
        )
