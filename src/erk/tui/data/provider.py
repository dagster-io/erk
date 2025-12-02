"""Data provider for TUI plan table."""

from abc import ABC, abstractmethod

from erk_shared.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata import (
    extract_plan_header_local_impl_at,
    extract_plan_header_remote_impl_at,
    extract_plan_header_worktree_name,
)
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation, PullRequestInfo, WorkflowRun
from erk_shared.impl_folder import read_issue_reference
from erk_shared.plan_store.types import Plan, PlanState

from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_relative_time,
    format_workflow_outcome,
    format_workflow_run_id,
    get_workflow_run_state,
)
from erk.core.pr_utils import select_display_pr
from erk.core.repo_discovery import NoRepoSentinel, RepoContext, ensure_erk_metadata_dir
from erk.tui.data.types import PlanFilters, PlanRowData


class PlanDataProvider(ABC):
    """Abstract base class for plan data providers.

    Defines the interface for fetching plan data for TUI display.
    """

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Fetch plans matching the given filters.

        Args:
            filters: Filter options for the query

        Returns:
            List of PlanRowData objects for display
        """
        ...


class RealPlanDataProvider(PlanDataProvider):
    """Production implementation that wraps PlanListService.

    Transforms PlanListData into PlanRowData for TUI display.
    """

    def __init__(self, ctx: ErkContext, location: GitHubRepoLocation) -> None:
        """Initialize with context and repository info.

        Args:
            ctx: ErkContext with all dependencies
            location: GitHub repository location (local root + repo identity)
        """
        self._ctx = ctx
        self._location = location

    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Fetch plans and transform to TUI row format.

        Args:
            filters: Filter options for the query

        Returns:
            List of PlanRowData objects for display
        """
        # Determine if we need workflow runs
        needs_workflow_runs = filters.show_runs or filters.run_state is not None

        # Fetch data via PlanListService
        # Note: PR linkages are always fetched via unified GraphQL query (no performance penalty)
        plan_data = self._ctx.plan_list_service.get_plan_list_data(
            location=self._location,
            labels=list(filters.labels),
            state=filters.state,
            limit=filters.limit,
            skip_workflow_runs=not needs_workflow_runs,
        )

        # Build local worktree mapping
        worktree_by_issue = self._build_worktree_mapping()

        # Transform to PlanRowData
        rows: list[PlanRowData] = []
        use_graphite = self._ctx.global_config.use_graphite if self._ctx.global_config else False

        for issue in plan_data.issues:
            plan = _issue_to_plan(issue)

            # Get workflow run for filtering
            workflow_run = plan_data.workflow_runs.get(issue.number)

            # Apply run_state filter
            if filters.run_state is not None:
                if workflow_run is None:
                    continue
                if get_workflow_run_state(workflow_run) != filters.run_state:
                    continue

            # Build row data
            row = self._build_row_data(
                plan=plan,
                issue_number=issue.number,
                pr_linkages=plan_data.pr_linkages,
                workflow_run=workflow_run,
                worktree_by_issue=worktree_by_issue,
                use_graphite=use_graphite,
            )
            rows.append(row)

        return rows

    def _build_worktree_mapping(self) -> dict[int, str]:
        """Build mapping of issue number to local worktree name."""
        _ensure_erk_metadata_dir_from_context(self._ctx.repo)
        worktree_by_issue: dict[int, str] = {}
        worktrees = self._ctx.git.list_worktrees(self._location.root)
        for worktree in worktrees:
            impl_folder = worktree.path / ".impl"
            if impl_folder.exists() and impl_folder.is_dir():
                issue_ref = read_issue_reference(impl_folder)
                if issue_ref is not None:
                    if issue_ref.issue_number not in worktree_by_issue:
                        worktree_by_issue[issue_ref.issue_number] = worktree.path.name
        return worktree_by_issue

    def _build_row_data(
        self,
        *,
        plan: Plan,
        issue_number: int,
        pr_linkages: dict[int, list[PullRequestInfo]],
        workflow_run: WorkflowRun | None,
        worktree_by_issue: dict[int, str],
        use_graphite: bool,
    ) -> PlanRowData:
        """Build a single PlanRowData from plan and related data."""
        # Truncate title
        title = plan.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Worktree info
        worktree_name = ""
        exists_locally = False

        if issue_number in worktree_by_issue:
            worktree_name = worktree_by_issue[issue_number]
            exists_locally = True

        # Extract from issue body
        if plan.body:
            extracted = extract_plan_header_worktree_name(plan.body)
            if extracted and not worktree_name:
                worktree_name = extracted
            last_local_impl_at = extract_plan_header_local_impl_at(plan.body)
            last_remote_impl_at = extract_plan_header_remote_impl_at(plan.body)
        else:
            last_local_impl_at = None
            last_remote_impl_at = None

        # Format time displays
        local_impl = format_relative_time(last_local_impl_at)
        local_impl_display = local_impl if local_impl else "-"
        remote_impl = format_relative_time(last_remote_impl_at)
        remote_impl_display = remote_impl if remote_impl else "-"

        # PR info
        pr_number: int | None = None
        pr_url: str | None = None
        pr_display = "-"
        checks_display = "-"

        if issue_number in pr_linkages:
            issue_prs = pr_linkages[issue_number]
            selected_pr = select_display_pr(issue_prs)
            if selected_pr is not None:
                pr_number = selected_pr.number
                graphite_url = self._ctx.graphite.get_graphite_url(
                    GitHubRepoId(selected_pr.owner, selected_pr.repo), selected_pr.number
                )
                pr_url = graphite_url if use_graphite and graphite_url else selected_pr.url
                emoji = get_pr_status_emoji(selected_pr)
                pr_display = f"#{selected_pr.number} {emoji}"
                checks_display = format_checks_cell(selected_pr)

        # Workflow run info
        run_id_display = "-"
        run_state_display = "-"

        if workflow_run is not None:
            workflow_url = None
            if plan.url:
                parts = plan.url.split("/")
                if len(parts) >= 5:
                    owner = parts[-4]
                    repo_name = parts[-3]
                    workflow_url = (
                        f"https://github.com/{owner}/{repo_name}/actions/runs/{workflow_run.run_id}"
                    )
            run_id_display = format_workflow_run_id(workflow_run, workflow_url)
            run_state_display = format_workflow_outcome(workflow_run)

        return PlanRowData(
            issue_number=issue_number,
            issue_url=plan.url,
            title=title,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_display=pr_display,
            checks_display=checks_display,
            worktree_name=worktree_name,
            exists_locally=exists_locally,
            local_impl_display=local_impl_display,
            remote_impl_display=remote_impl_display,
            run_id_display=run_id_display,
            run_state_display=run_state_display,
        )


def _issue_to_plan(issue: IssueInfo) -> Plan:
    """Convert IssueInfo to Plan format."""
    state = PlanState.OPEN if issue.state == "OPEN" else PlanState.CLOSED
    return Plan(
        plan_identifier=str(issue.number),
        title=issue.title,
        body=issue.body,
        state=state,
        url=issue.url,
        labels=issue.labels,
        assignees=issue.assignees,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        metadata={"number": issue.number},
    )


def _ensure_erk_metadata_dir_from_context(repo: RepoContext | NoRepoSentinel) -> None:
    """Ensure erk metadata directory exists, handling sentinel case."""
    if isinstance(repo, RepoContext):
        ensure_erk_metadata_dir(repo)
