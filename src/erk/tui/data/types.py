"""Data types for TUI components."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from erk_shared.gateway.github.types import IssueFilterState


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
        objective_deps_display: Dep status of next node ("ready", "in progress", "-").
        objective_deps_plans: Tuple of (display, url) pairs for blocking dep plans.
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
    checks_passing: bool | None
    checks_counts: tuple[int, int] | None
    ci_summary_comment_id: int | None
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
    objective_deps_display: str
    objective_deps_plans: tuple[tuple[str, str], ...]
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
class RunRowData:
    """Row data for displaying a workflow run in the TUI Runs tab.

    Contains pre-formatted display strings and raw data needed for actions.
    Immutable to ensure table state consistency.

    Attributes:
        run_id: GitHub Actions workflow run ID string.
        run_url: URL to the GitHub Actions run page. None if unavailable.
        status: Raw run status ("queued", "in_progress", "completed").
        conclusion: Raw run conclusion ("success", "failure", "cancelled"). None if in progress.
        status_display: Pre-formatted status string for table display.
        workflow_name: Workflow command name (e.g., "plan-implement", "pr-address").
        pr_number: Linked PR number. None if no PR.
        pr_url: URL to the linked PR. None if no PR.
        pr_display: Formatted PR cell content (e.g., "#123" or "-").
        pr_title: PR title. None if no PR.
        pr_state: PR state ("OPEN", "MERGED", "CLOSED"). None if no PR linked.
        title_display: Truncated title for table display.
        submitted_display: Formatted submission time (e.g., "03-09 14:30").
        created_at: UTC datetime when run was created. None if unavailable.
        checks_display: Formatted checks cell content.
        run_id_display: Formatted run ID for display.
        branch_display: Branch name, truncated to 40 chars.
        branch: Branch name from the workflow run (e.g., "plnd/fix-widget-9039").
    """

    run_id: str
    run_url: str | None
    status: str
    conclusion: str | None
    status_display: str
    workflow_name: str
    pr_number: int | None
    pr_url: str | None
    pr_display: str
    pr_title: str | None
    pr_state: str | None
    title_display: str
    branch_display: str
    submitted_display: str
    created_at: datetime | None
    checks_display: str
    run_id_display: str
    branch: str


@dataclass(frozen=True)
class FetchTimings:
    """Timing breakdown for a single fetch cycle.

    All values are in milliseconds. The summary() method produces a
    compact one-line string suitable for the status bar.
    """

    rest_issues_ms: float
    graphql_enrich_ms: float
    plan_parsing_ms: float
    workflow_runs_ms: float
    worktree_mapping_ms: float
    row_building_ms: float
    total_ms: float
    warnings: tuple[str, ...] = ()

    def summary(self) -> str:
        """One-line summary for status bar: 'rest:1.2 gql:2.3 wf:0.8 = 4.6s'."""
        entries = [
            ("rest", self.rest_issues_ms, 0),
            ("gql", self.graphql_enrich_ms, 0),
            ("parse", self.plan_parsing_ms, 100),
            ("wf", self.workflow_runs_ms, 0),
            ("wt", self.worktree_mapping_ms, 100),
            ("rows", self.row_building_ms, 100),
        ]
        parts = [f"{label}:{ms / 1000:.1f}" for label, ms, threshold in entries if ms > threshold]
        return " ".join(parts) + f" = {self.total_ms / 1000:.1f}s"


@dataclass(frozen=True)
class PlanFilters:
    """Filter options for plan list queries.

    Matches options from the existing CLI command for consistency.

    Attributes:
        labels: Labels to filter by (default: ["erk-pr"])
        state: Filter by state ("open" or "closed")
        run_state: Filter by workflow run state (e.g., "in_progress")
        limit: Maximum number of results (None for no limit)
        show_prs: Whether to include PR data
        show_runs: Whether to include workflow run data
        creator: Filter by creator username (None for all users)
        show_pr_column: Whether to show PR column in table
        lifecycle_stage: Filter by lifecycle stage (e.g., "impl", "planned")
    """

    labels: tuple[str, ...]
    state: IssueFilterState
    run_state: str | None
    limit: int | None
    show_prs: bool
    show_runs: bool
    exclude_labels: tuple[str, ...]
    creator: str | None = None
    show_pr_column: bool = True
    lifecycle_stage: str | None = None

    @staticmethod
    def default() -> PlanFilters:
        """Create default filters (open erk-pr issues)."""
        return PlanFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
            creator=None,
        )


def serialize_plan_row(row: PlanRowData) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict.

    Handles datetime fields (to ISO 8601 strings) and tuple fields
    (log_entries, objective_deps_plans) to lists for JSON compatibility.
    """
    data = dataclasses.asdict(row)
    for key in ("last_local_impl_at", "last_remote_impl_at", "updated_at", "created_at"):
        if isinstance(data[key], datetime):
            data[key] = data[key].isoformat()
    # Convert log_entries tuple of tuples to list of lists
    data["log_entries"] = [list(entry) for entry in row.log_entries]
    # Convert objective_deps_plans tuple of tuples to list of lists
    data["objective_deps_plans"] = [list(entry) for entry in row.objective_deps_plans]
    return data
