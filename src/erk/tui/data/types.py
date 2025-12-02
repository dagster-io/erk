"""Data types for TUI components."""

from dataclasses import dataclass


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
    """

    labels: tuple[str, ...]
    state: str | None
    run_state: str | None
    limit: int | None
    show_prs: bool
    show_runs: bool

    @staticmethod
    def default() -> "PlanFilters":
        """Create default filters (open erk-plan issues)."""
        return PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
        )
