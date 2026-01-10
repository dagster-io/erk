"""Data provider for TUI plan table."""

import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

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
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.http.abc import HttpClient
from erk_shared.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
    extract_plan_header_local_impl_at,
    extract_plan_header_remote_impl_at,
    extract_plan_header_worktree_name,
)
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation, PullRequestInfo, WorkflowRun
from erk_shared.naming import extract_leading_issue_number
from erk_shared.plan_store.types import Plan, PlanState


class PlanDataProvider(ABC):
    """Abstract base class for plan data providers.

    Defines the interface for fetching plan data for TUI display.
    """

    @property
    @abstractmethod
    def repo_root(self) -> Path:
        """Get the repository root path.

        Returns:
            Path to the repository root directory
        """
        ...

    @property
    @abstractmethod
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations.

        Returns:
            Clipboard interface for copying to system clipboard
        """
        ...

    @property
    @abstractmethod
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs.

        Returns:
            BrowserLauncher interface for opening URLs in browser
        """
        ...

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        """Fetch plans matching the given filters.

        Args:
            filters: Filter options for the query

        Returns:
            List of PlanRowData objects for display
        """
        ...

    @abstractmethod
    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close a plan and its linked PRs.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        ...

    @abstractmethod
    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit a plan to the implementation queue.

        Args:
            issue_number: The issue number to submit
            issue_url: The issue URL for repository context
        """
        ...

    @abstractmethod
    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Examines commits on each local branch (not in trunk) to determine
        the most recent activity.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of issue_number to BranchActivity for plans with local worktrees.
            Plans without local worktrees are not included in the result.
        """
        ...

    @abstractmethod
    def fetch_plan_content(self, issue_number: int, issue_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue.

        Args:
            issue_number: The GitHub issue number
            issue_body: The issue body (to extract plan_comment_id from metadata)

        Returns:
            The extracted plan content, or None if not found
        """
        ...


class RealPlanDataProvider(PlanDataProvider):
    """Production implementation that wraps PlanListService.

    Transforms PlanListData into PlanRowData for TUI display.
    """

    def __init__(
        self,
        ctx: ErkContext,
        *,
        location: GitHubRepoLocation,
        clipboard: Clipboard,
        browser: BrowserLauncher,
        http_client: HttpClient,
    ) -> None:
        """Initialize with context and repository info.

        Args:
            ctx: ErkContext with all dependencies
            location: GitHub repository location (local root + repo identity)
            clipboard: Clipboard interface for copy operations
            browser: BrowserLauncher interface for opening URLs
            http_client: HTTP client for direct API calls (faster than subprocess)
        """
        self._ctx = ctx
        self._location = location
        self._clipboard = clipboard
        self._browser = browser
        self._http_client = http_client

    @property
    def repo_root(self) -> Path:
        """Get the repository root path."""
        return self._location.root

    @property
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        return self._clipboard

    @property
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs."""
        return self._browser

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
            creator=filters.creator,
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

    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        """Close a plan and its linked PRs using direct HTTP calls.

        This method uses the HTTP client directly instead of subprocess calls
        for significantly faster execution in the TUI.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        # Parse owner/repo from issue URL
        owner_repo = self._parse_owner_repo_from_url(issue_url)
        if owner_repo is None:
            return []
        owner, repo = owner_repo

        # Close linked PRs first
        closed_prs = self._close_linked_prs_http(issue_number, owner, repo)

        # Close the plan (issue) via HTTP
        self._http_client.patch(
            f"repos/{owner}/{repo}/issues/{issue_number}",
            data={"state": "closed"},
        )

        return closed_prs

    def _parse_owner_repo_from_url(self, url: str) -> tuple[str, str] | None:
        """Parse owner and repo from a GitHub URL.

        Args:
            url: GitHub URL (e.g., "https://github.com/owner/repo/issues/123")

        Returns:
            Tuple of (owner, repo) or None if parsing fails
        """
        # URL format: https://github.com/owner/repo/...
        if not url.startswith("https://github.com/"):
            return None
        parts = url.split("/")
        # parts: ['https:', '', 'github.com', 'owner', 'repo', ...]
        if len(parts) < 5:
            return None
        return (parts[3], parts[4])

    def _close_linked_prs_http(
        self,
        issue_number: int,
        owner: str,
        repo: str,
    ) -> list[int]:
        """Close all OPEN PRs linked to an issue using HTTP.

        Uses the GitHub REST API via HTTP client for fast execution.

        Args:
            issue_number: The issue number
            owner: Repository owner
            repo: Repository name

        Returns:
            List of PR numbers that were closed
        """
        # Use the existing gateway to get PR linkages (still efficient for read)
        location = GitHubRepoLocation(
            root=self._location.root,
            repo_id=GitHubRepoId(owner=owner, repo=repo),
        )
        pr_linkages = self._ctx.github.get_prs_linked_to_issues(location, [issue_number])
        linked_prs = pr_linkages.get(issue_number, [])

        closed_prs: list[int] = []
        for pr in linked_prs:
            if pr.state == "OPEN":
                # Close via HTTP client for speed
                self._http_client.patch(
                    f"repos/{owner}/{repo}/pulls/{pr.number}",
                    data={"state": "closed"},
                )
                closed_prs.append(pr.number)

        return closed_prs

    def submit_to_queue(self, issue_number: int, issue_url: str) -> None:
        """Submit a plan to the implementation queue.

        Runs 'erk plan submit' as a subprocess to handle the complex workflow
        of creating branches, PRs, and triggering GitHub Actions.

        Args:
            issue_number: The issue number to submit
            issue_url: The issue URL (unused, kept for interface consistency)
        """
        # Run erk plan submit command from the repository root
        subprocess.run(
            ["erk", "plan", "submit", str(issue_number)],
            cwd=self._location.root,
            check=True,
            capture_output=True,
        )

    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of issue_number to BranchActivity for plans with local worktrees.
        """
        result: dict[int, BranchActivity] = {}

        # Get trunk branch
        trunk = self._ctx.git.detect_trunk_branch(self._location.root)

        for row in rows:
            # Only fetch for plans with local branches
            if not row.exists_locally or row.worktree_branch is None:
                continue

            # Get commits on branch not in trunk
            commits = self._ctx.git.get_branch_commits_with_authors(
                self._location.root,
                row.worktree_branch,
                trunk,
                limit=1,  # Only need most recent
            )

            if commits:
                # Parse ISO timestamp from git
                timestamp_str = commits[0]["timestamp"]
                commit_at = datetime.fromisoformat(timestamp_str)
                result[row.issue_number] = BranchActivity(
                    last_commit_at=commit_at,
                    last_commit_author=commits[0]["author"],
                )
            else:
                result[row.issue_number] = BranchActivity.empty()

        return result

    def fetch_plan_content(self, issue_number: int, issue_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue.

        Uses the plan_comment_id from the issue body metadata to fetch
        the specific comment containing the plan content.

        Args:
            issue_number: The GitHub issue number
            issue_body: The issue body (to extract plan_comment_id from metadata)

        Returns:
            The extracted plan content, or None if not found
        """
        # Extract plan_comment_id from issue body metadata
        comment_id = extract_plan_header_comment_id(issue_body)
        if comment_id is None:
            return None

        # Fetch the comment via HTTP client
        owner = self._location.repo_id.owner
        repo = self._location.repo_id.repo
        endpoint = f"repos/{owner}/{repo}/issues/comments/{comment_id}"

        response = self._http_client.get(endpoint)
        comment_body = response.get("body", "")

        # Extract plan content from comment
        return extract_plan_from_comment(comment_body)

    def _build_worktree_mapping(self) -> dict[int, tuple[str, str | None]]:
        """Build mapping of issue number to (worktree name, branch).

        Uses PXXXX prefix matching on branch names to associate worktrees
        with issues. Branch names follow pattern: P{issue_number}-{slug}-{timestamp}

        Returns:
            Mapping of issue number to tuple of (worktree_name, branch_name)
        """
        _ensure_erk_metadata_dir_from_context(self._ctx.repo)
        worktree_by_issue: dict[int, tuple[str, str | None]] = {}
        worktrees = self._ctx.git.list_worktrees(self._location.root)
        for worktree in worktrees:
            issue_number = (
                extract_leading_issue_number(worktree.branch) if worktree.branch else None
            )
            if issue_number is not None:
                if issue_number not in worktree_by_issue:
                    worktree_by_issue[issue_number] = (
                        worktree.path.name,
                        worktree.branch,
                    )
        return worktree_by_issue

    def _build_row_data(
        self,
        *,
        plan: Plan,
        issue_number: int,
        pr_linkages: dict[int, list[PullRequestInfo]],
        workflow_run: WorkflowRun | None,
        worktree_by_issue: dict[int, tuple[str, str | None]],
        use_graphite: bool,
    ) -> PlanRowData:
        """Build a single PlanRowData from plan and related data."""
        # Truncate title for display
        title = plan.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Store full title
        full_title = plan.title

        # Worktree info
        worktree_name = ""
        worktree_branch: str | None = None
        exists_locally = False

        if issue_number in worktree_by_issue:
            worktree_name, worktree_branch = worktree_by_issue[issue_number]
            exists_locally = True

        # Extract from issue body
        local_impl_str: str | None = None
        remote_impl_str: str | None = None
        if plan.body:
            extracted = extract_plan_header_worktree_name(plan.body)
            if extracted and not worktree_name:
                worktree_name = extracted
            local_impl_str = extract_plan_header_local_impl_at(plan.body)
            remote_impl_str = extract_plan_header_remote_impl_at(plan.body)

        # Parse ISO 8601 timestamps for storage
        last_local_impl_at: datetime | None = None
        last_remote_impl_at: datetime | None = None
        if local_impl_str:
            last_local_impl_at = datetime.fromisoformat(local_impl_str.replace("Z", "+00:00"))
        if remote_impl_str:
            last_remote_impl_at = datetime.fromisoformat(remote_impl_str.replace("Z", "+00:00"))

        # Format time displays
        local_impl = format_relative_time(local_impl_str)
        local_impl_display = local_impl if local_impl else "-"
        remote_impl = format_relative_time(remote_impl_str)
        remote_impl_display = remote_impl if remote_impl else "-"

        # PR info
        pr_number: int | None = None
        pr_url: str | None = None
        pr_title: str | None = None
        pr_state: str | None = None
        pr_display = "-"
        checks_display = "-"

        if issue_number in pr_linkages:
            issue_prs = pr_linkages[issue_number]
            selected_pr = select_display_pr(issue_prs)
            if selected_pr is not None:
                pr_number = selected_pr.number
                pr_title = selected_pr.title
                pr_state = selected_pr.state
                graphite_url = self._ctx.graphite.get_graphite_url(
                    GitHubRepoId(selected_pr.owner, selected_pr.repo), selected_pr.number
                )
                pr_url = graphite_url if use_graphite and graphite_url else selected_pr.url
                emoji = get_pr_status_emoji(selected_pr)
                if selected_pr.will_close_target:
                    emoji += "🔗"
                pr_display = f"#{selected_pr.number} {emoji}"
                checks_display = format_checks_cell(selected_pr)

        # Workflow run info
        run_id: str | None = None
        run_status: str | None = None
        run_conclusion: str | None = None
        run_id_display = "-"
        run_state_display = "-"
        run_url: str | None = None

        if workflow_run is not None:
            run_id = str(workflow_run.run_id)
            run_status = workflow_run.status
            run_conclusion = workflow_run.conclusion
            if plan.url:
                parts = plan.url.split("/")
                if len(parts) >= 5:
                    owner = parts[-4]
                    repo_name = parts[-3]
                    run_url = (
                        f"https://github.com/{owner}/{repo_name}/actions/runs/{workflow_run.run_id}"
                    )
            run_id_display = format_workflow_run_id(workflow_run, run_url)
            run_state_display = format_workflow_outcome(workflow_run)

        # Log entries (empty for now - will be fetched on demand in the modal)
        log_entries: tuple[tuple[str, str, str], ...] = ()

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
            run_url=run_url,
            full_title=full_title,
            issue_body=plan.body or "",
            pr_title=pr_title,
            pr_state=pr_state,
            worktree_branch=worktree_branch,
            last_local_impl_at=last_local_impl_at,
            last_remote_impl_at=last_remote_impl_at,
            run_id=run_id,
            run_status=run_status,
            run_conclusion=run_conclusion,
            log_entries=log_entries,
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
