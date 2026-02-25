"""Data types for TUI components."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PlanRowData:
    """Row data for displaying a plan in the TUI table.

    Contains pre-formatted display strings and raw data needed for actions.
    Immutable to ensure table state consistency.

    **Display vs Raw convention:** Many data points have both a raw field (for
    logic/predicates) and a display field (for table rendering). Raw fields are
    often nullable (None when absent), while display fields are always strings
    (dash "-" or empty when absent). Use raw fields in availability predicates
    (``ctx.row.pr_number is not None``), display fields for rendering.

    Attributes:

        plan_id: GitHub issue number (e.g., 123). Never None.
        plan_url: Full URL to the GitHub issue. None when unavailable.
        full_title: Complete untruncated plan title. Empty string possible.
        plan_body: Raw issue body text (markdown). Empty string possible.

        pr_number: PR number if linked, None otherwise.
        pr_url: URL to PR (GitHub or Graphite), None if no PR.
        pr_display: Formatted PR cell content (e.g., "#123 👀"). Always a string.
        pr_title: PR title if different from issue title. None if no PR.
        pr_state: PR state ("OPEN", "MERGED", "CLOSED"). None if no PR.
        pr_head_branch: Head branch from PR metadata (source branch for landing).
            None if no PR.
        checks_display: Formatted checks cell (e.g., "✓" or "✗"). Always a string.
        resolved_comment_count: Count of resolved PR review comments. 0 if no PR.
        total_comment_count: Total count of PR review comments. 0 if no PR.
        comments_display: Formatted comment counts (e.g., "3/5" or "-").

        worktree_name: Name of local worktree. Empty string if none.
        worktree_branch: Branch name in the worktree. None if no worktree.
        exists_locally: Whether worktree exists on this machine.

        local_impl_display: Relative time since last local impl (e.g., "2h ago").
        remote_impl_display: Relative time since last remote impl.
        last_local_impl_at: Raw datetime for local impl. None if never run.
        last_remote_impl_at: Raw datetime for remote impl. None if never run.

        run_id: Raw workflow run ID. None if no run.
        run_id_display: Formatted workflow run ID for display.
        run_url: URL to the GitHub Actions run page. None if no run.
        run_status: Run status ("completed", "in_progress", "queued"). None if no run.
        run_conclusion: Run conclusion ("success", "failure", "cancelled").
            None if no run or still in progress.
        run_state_display: Formatted workflow run state.

        log_entries: Tuple of (event_name, timestamp, comment_url) for the plan
            activity log. Empty tuple when no log entries.

        learn_status: Raw learn status value from plan header. None if absent.
        learn_plan_issue: Plan issue number (for completed_with_plan status).
        learn_plan_issue_closed: Whether the learn plan issue is closed.
        learn_plan_pr: PR number (for plan_completed status).
        learn_run_url: URL to GitHub Actions workflow run (for pending status).
        learn_display: Formatted display string (e.g., "- not started", "⟳ in progress").
        learn_display_icon: Icon-only display for table ("-", "⟳", "∅", "#456", "✓ #12").

        objective_issue: Objective issue number. None if not linked to an objective.
        objective_url: Full URL to the objective issue. None if no objective.
        objective_display: Formatted display string (e.g., "#123" or "-").
        objective_done_nodes: Count of done nodes in objective roadmap. 0 if no objective.
        objective_total_nodes: Total nodes in objective roadmap. 0 if no objective.
        objective_progress_display: Progress display (e.g., "3/7" or "-").
        objective_slug_display: Slug or stripped title fallback (max 25 chars).
        objective_state_display: Sparkline string (e.g., "✓✓✓▶▶○○○○").
        objective_head_state: Head state of next node ("in progress", "ready", "-").
        objective_head_plans: Tuple of (display, url) pairs for blocking head plans.
            Each entry is a plan number like "#7911" paired with its GitHub URL.
            Empty tuple when no blocking deps have associated plans.
        objective_next_node_display: Next node ID display (e.g., "1.1" or "-").

        updated_at: Last update datetime of the issue.
        updated_display: Formatted relative time for last update (e.g., "2h ago").
        created_at: Creation datetime of the issue.
        created_display: Formatted relative time string (e.g., "2d ago").
        author: GitHub login of the issue creator.
        is_learn_plan: Whether this is a learn plan (has [erk-learn] prefix).
        lifecycle_display: Formatted lifecycle stage (e.g., "planned", "impl", "-").
        status_display: Status indicator emojis (e.g., "🚀", "👀 💥", "-").
    """

    plan_id: int
    plan_url: str | None
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
    plan_body: str
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
    learn_plan_issue_closed: bool | None
    learn_plan_pr: int | None
    learn_run_url: str | None
    learn_display: str
    learn_display_icon: str
    objective_issue: int | None
    objective_url: str | None
    objective_display: str
    objective_done_nodes: int
    objective_total_nodes: int
    objective_progress_display: str
    objective_slug_display: str
    objective_state_display: str
    objective_head_state: str
    objective_head_plans: tuple[tuple[str, str], ...]
    objective_next_node_display: str
    updated_at: datetime
    updated_display: str
    created_at: datetime
    created_display: str
    author: str
    is_learn_plan: bool
    lifecycle_display: str
    status_display: str


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
        show_pr_column: Whether to show PR column in table
        lifecycle_stage: Filter by lifecycle stage (e.g., "impl", "planned")
    """

    labels: tuple[str, ...]
    state: str | None
    run_state: str | None
    limit: int | None
    show_prs: bool
    show_runs: bool
    creator: str | None = None
    show_pr_column: bool = True
    lifecycle_stage: str | None = None
    exclude_labels: tuple[str, ...] = ()

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
