"""Real implementation of PlanDataProvider for production use."""

import logging
import subprocess
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
from erk_shared.gateway.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_objective_from_comment,
    extract_objective_header_comment_id,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    _TERMINAL_STATUSES,
    build_graph,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
)
from erk_shared.gateway.github.metadata.roadmap import (
    parse_roadmap,
)
from erk_shared.gateway.github.metadata.schemas import (
    LAST_LOCAL_IMPL_AT,
    LAST_REMOTE_IMPL_AT,
    LEARN_PLAN_ISSUE,
    LEARN_PLAN_PR,
    LEARN_RUN_ID,
    LEARN_STATUS,
    OBJECTIVE_ISSUE,
    REVIEW_PR,
    WORKTREE_NAME,
)
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRReviewThread,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.http.abc import HttpClient
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider
from erk_shared.naming import extract_leading_issue_number
from erk_shared.plan_store.conversion import (
    header_datetime,
    header_int,
    header_str,
)
from erk_shared.plan_store.types import Plan

logger = logging.getLogger(__name__)


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
        worktree_by_plan_id = self._build_worktree_mapping()

        # Use pre-converted Plan objects from PlanListData
        plans = plan_data.plans

        # First pass: collect learn_plan_issue numbers for batch fetch
        learn_issue_numbers: set[int] = set()
        for plan in plans:
            learn_plan_issue = header_int(plan.header_fields, LEARN_PLAN_ISSUE)
            if learn_plan_issue is not None:
                learn_issue_numbers.add(learn_plan_issue)

        # Batch fetch learn issue states
        learn_issue_states = self._fetch_learn_issue_states(learn_issue_numbers)

        # Transform to PlanRowData
        rows: list[PlanRowData] = []
        use_graphite = self._ctx.global_config.use_graphite if self._ctx.global_config else False

        for plan in plans:
            plan_id = int(plan.plan_identifier)

            # Get workflow run for filtering
            workflow_run = plan_data.workflow_runs.get(plan_id)

            # Apply run_state filter
            if filters.run_state is not None:
                if workflow_run is None:
                    continue
                if get_workflow_run_state(workflow_run) != filters.run_state:
                    continue

            # Build row data
            row = self._build_row_data(
                plan=plan,
                plan_id=plan_id,
                pr_linkages=plan_data.pr_linkages,
                workflow_run=workflow_run,
                worktree_by_plan_id=worktree_by_plan_id,
                use_graphite=use_graphite,
                learn_issue_states=learn_issue_states,
            )
            rows.append(row)

        return rows

    def _fetch_learn_issue_states(
        self,
        issue_numbers: set[int],
    ) -> dict[int, bool]:
        """Batch fetch issue closed states for learn plan issues.

        Args:
            issue_numbers: Set of issue numbers to fetch

        Returns:
            Mapping of issue number to is_closed (True if closed, False if open)
        """
        result: dict[int, bool] = {}
        for issue_number in issue_numbers:
            issue_info = self._ctx.github.issues.get_issue(self._location.root, issue_number)
            if isinstance(issue_info, IssueNotFound):
                # Issue not found - log and skip
                logger.debug("Could not fetch learn issue %d: issue not found", issue_number)
                continue
            result[issue_number] = issue_info.state == "CLOSED"
        return result

    def close_plan(self, plan_id: int, plan_url: str) -> list[int]:
        """Close a plan and its linked PRs using direct HTTP calls.

        This method uses the HTTP client directly instead of subprocess calls
        for significantly faster execution in the TUI.

        Args:
            plan_id: The plan ID to close
            plan_url: The plan URL for PR linkage lookup

        Returns:
            List of PR numbers that were also closed
        """
        # Parse owner/repo from issue URL
        owner_repo = self._parse_owner_repo_from_url(plan_url)
        if owner_repo is None:
            return []
        owner, repo = owner_repo

        # Close linked PRs first
        closed_prs = self._close_linked_prs_http(plan_id, owner, repo)

        # Close the plan (issue) via HTTP
        self._http_client.patch(
            f"repos/{owner}/{repo}/issues/{plan_id}",
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
        plan_id: int,
        owner: str,
        repo: str,
    ) -> list[int]:
        """Close all OPEN PRs linked to an issue using HTTP.

        Uses the GitHub REST API via HTTP client for fast execution.

        Args:
            plan_id: The plan ID
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
        pr_linkages = self._ctx.github.get_prs_linked_to_issues(location, [plan_id])
        linked_prs = pr_linkages.get(plan_id, [])

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

    def update_objective_after_land(
        self,
        *,
        objective_issue: int,
        pr_num: int,
        branch: str,
    ) -> None:
        """Update an objective after landing a PR.

        Runs 'erk exec objective-update-after-land' as a subprocess.

        Args:
            objective_issue: The objective issue number to update
            pr_num: The PR number that was landed
            branch: The PR head branch name
        """
        result = subprocess.run(
            [
                "erk",
                "exec",
                "objective-update-after-land",
                f"--objective={objective_issue}",
                f"--pr={pr_num}",
                f"--branch={branch}",
            ],
            cwd=self._location.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"objective-update-after-land failed: {result.stdout}")

    def submit_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Submit a plan to the implementation queue.

        Runs 'erk plan submit' as a subprocess to handle the complex workflow
        of creating branches, PRs, and triggering GitHub Actions.

        Args:
            plan_id: The plan ID to submit
            plan_url: The plan URL (unused, kept for interface consistency)
        """
        # Run erk plan submit command from the repository root
        # -f flag prevents blocking on existing branch prompts in TUI context
        subprocess.run(
            ["erk", "plan", "submit", str(plan_id), "-f"],
            cwd=self._location.root,
            check=True,
            capture_output=True,
        )

    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of plan_id to BranchActivity for plans with local worktrees.
        """
        result: dict[int, BranchActivity] = {}

        # Get trunk branch
        trunk = self._ctx.git.branch.detect_trunk_branch(self._location.root)

        for row in rows:
            # Only fetch for plans with local branches
            if not row.exists_locally or row.worktree_branch is None:
                continue

            # Get commits on branch not in trunk
            commits = self._ctx.git.branch.get_branch_commits_with_authors(
                self._location.root,
                row.worktree_branch,
                trunk,
                limit=1,  # Only need most recent
            )

            if commits:
                # Parse ISO timestamp from git
                timestamp_str = commits[0]["timestamp"]
                commit_at = datetime.fromisoformat(timestamp_str)
                result[row.plan_id] = BranchActivity(
                    last_commit_at=commit_at,
                    last_commit_author=commits[0]["author"],
                )
            else:
                result[row.plan_id] = BranchActivity.empty()

        return result

    def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fetch plan content from the first comment of an issue.

        Uses the plan_comment_id from the issue body metadata to fetch
        the specific comment containing the plan content.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (to extract plan_comment_id from metadata)

        Returns:
            The extracted plan content, or None if not found
        """
        # Extract plan_comment_id from issue body metadata
        comment_id = extract_plan_header_comment_id(plan_body)
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

    def fetch_objective_content(self, plan_id: int, plan_body: str) -> str | None:
        """Fetch objective content from the first comment of an issue.

        Uses the objective_comment_id from the issue body metadata to fetch
        the specific comment containing the objective content.

        Args:
            plan_id: The GitHub issue number
            plan_body: The issue body (to extract objective_comment_id from metadata)

        Returns:
            The extracted objective content, or None if not found
        """
        comment_id = extract_objective_header_comment_id(plan_body)
        if comment_id is None:
            return None

        owner = self._location.repo_id.owner
        repo = self._location.repo_id.repo
        endpoint = f"repos/{owner}/{repo}/issues/comments/{comment_id}"

        response = self._http_client.get(endpoint)
        comment_body = response.get("body", "")

        return extract_objective_from_comment(comment_body)

    def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
        """Fetch unresolved review threads for a pull request.

        Args:
            pr_number: The PR number to fetch threads for

        Returns:
            List of unresolved PRReviewThread objects sorted by (path, line)
        """
        return self._ctx.github.get_pr_review_threads(
            self._location.root, pr_number, include_resolved=False
        )

    def _build_worktree_mapping(self) -> dict[int, tuple[str, str | None]]:
        """Build mapping of plan ID to (worktree name, branch).

        Uses PXXXX prefix matching on branch names to associate worktrees
        with issues. Branch names follow pattern: P{plan_id}-{slug}-{timestamp}

        Returns:
            Mapping of plan ID to tuple of (worktree_name, branch_name)
        """
        _ensure_erk_metadata_dir_from_context(self._ctx.repo)
        worktree_by_plan_id: dict[int, tuple[str, str | None]] = {}
        worktrees = self._ctx.git.worktree.list_worktrees(self._location.root)
        for worktree in worktrees:
            issue_number = (
                extract_leading_issue_number(worktree.branch) if worktree.branch else None
            )
            if issue_number is not None:
                if issue_number not in worktree_by_plan_id:
                    worktree_by_plan_id[issue_number] = (
                        worktree.path.name,
                        worktree.branch,
                    )
        return worktree_by_plan_id

    def _build_row_data(
        self,
        *,
        plan: Plan,
        plan_id: int,
        pr_linkages: dict[int, list[PullRequestInfo]],
        workflow_run: WorkflowRun | None,
        worktree_by_plan_id: dict[int, tuple[str, str | None]],
        use_graphite: bool,
        learn_issue_states: dict[int, bool],
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

        if plan_id in worktree_by_plan_id:
            worktree_name, worktree_branch = worktree_by_plan_id[plan_id]
            exists_locally = True

        # Extract from pre-parsed header fields (no repeated YAML parsing)
        local_impl_str: str | None = None
        remote_impl_str: str | None = None
        learn_status: str | None = None
        learn_plan_issue: int | None = None
        learn_plan_pr: int | None = None
        learn_run_id: str | None = None
        review_pr: int | None = None
        if plan.header_fields:
            extracted = header_str(plan.header_fields, WORKTREE_NAME)
            if extracted and not worktree_name:
                worktree_name = extracted
            local_impl_str = header_str(plan.header_fields, LAST_LOCAL_IMPL_AT)
            remote_impl_str = header_str(plan.header_fields, LAST_REMOTE_IMPL_AT)
            learn_status = header_str(plan.header_fields, LEARN_STATUS)
            learn_plan_issue = header_int(plan.header_fields, LEARN_PLAN_ISSUE)
            learn_plan_pr = header_int(plan.header_fields, LEARN_PLAN_PR)
            learn_run_id = header_str(plan.header_fields, LEARN_RUN_ID)
            review_pr = header_int(plan.header_fields, REVIEW_PR)

        # Extract objective_issue from pre-parsed header fields
        objective_issue = header_int(plan.header_fields, OBJECTIVE_ISSUE)

        # Look up learn plan issue closed state
        learn_plan_issue_closed: bool | None = None
        if learn_plan_issue is not None and learn_plan_issue in learn_issue_states:
            learn_plan_issue_closed = learn_issue_states[learn_plan_issue]

        # Format learn display (full text for detail modal, icon-only for table)
        learn_display = _format_learn_display(
            learn_status,
            learn_plan_issue,
            learn_plan_pr,
            learn_plan_issue_closed=learn_plan_issue_closed,
        )
        learn_display_icon = _format_learn_display_icon(
            learn_status,
            learn_plan_issue,
            learn_plan_pr,
            learn_plan_issue_closed=learn_plan_issue_closed,
        )

        # Get datetime versions for storage (already parsed by YAML)
        last_local_impl_at = header_datetime(plan.header_fields, LAST_LOCAL_IMPL_AT)
        last_remote_impl_at = header_datetime(plan.header_fields, LAST_REMOTE_IMPL_AT)

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
        pr_head_branch: str | None = None
        pr_display = "-"
        checks_display = "-"

        # Comment counts - "-" when no PR
        resolved_comment_count = 0
        total_comment_count = 0
        comments_display = "-"

        if plan_id in pr_linkages:
            issue_prs = pr_linkages[plan_id]
            if review_pr is not None:
                exclude_pr_numbers: set[int] | None = {review_pr}
            else:
                exclude_pr_numbers = None
            selected_pr = select_display_pr(issue_prs, exclude_pr_numbers=exclude_pr_numbers)
            if selected_pr is not None:
                pr_number = selected_pr.number
                pr_title = selected_pr.title
                pr_state = selected_pr.state
                pr_head_branch = selected_pr.head_branch
                graphite_url = self._ctx.graphite.get_graphite_url(
                    GitHubRepoId(selected_pr.owner, selected_pr.repo), selected_pr.number
                )
                pr_url = graphite_url if use_graphite and graphite_url else selected_pr.url
                emoji = get_pr_status_emoji(selected_pr)
                if selected_pr.will_close_target:
                    emoji += "🔗"
                pr_display = f"#{selected_pr.number} {emoji}"
                checks_display = format_checks_cell(selected_pr)

                # Get review thread counts from batched PR data
                if selected_pr.review_thread_counts is not None:
                    resolved_comment_count, total_comment_count = selected_pr.review_thread_counts
                    comments_display = f"{resolved_comment_count}/{total_comment_count}"
                else:
                    comments_display = "0/0"

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

        # Build learn_run_url for pending status
        learn_run_url: str | None = None
        if learn_run_id is not None and plan.url is not None:
            parts = plan.url.split("/")
            if len(parts) >= 5:
                owner = parts[-4]
                repo_name = parts[-3]
                learn_run_url = (
                    f"https://github.com/{owner}/{repo_name}/actions/runs/{learn_run_id}"
                )

        # Format objective display
        objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

        # Parse roadmap for objective-specific fields
        objective_done_nodes = 0
        objective_total_nodes = 0
        objective_progress_display = "-"
        objective_next_node_display = "-"
        objective_deps_display = "-"
        if plan.body:
            phases, _errors = parse_roadmap(plan.body)
            if phases:
                graph = build_graph(phases)
                summary = compute_graph_summary(graph)
                objective_done_nodes = summary["done"]
                objective_total_nodes = summary["total_nodes"]
                objective_progress_display = f"{objective_done_nodes}/{objective_total_nodes}"
                next_node = find_graph_next_node(graph, phases)
                if next_node is not None:
                    step_text = f"{next_node['id']} {next_node['description']}"
                    if len(step_text) > 60:
                        step_text = step_text[:57] + "..."
                    objective_next_node_display = step_text
                    min_status = graph.min_dep_status(next_node["id"])
                    if min_status is None or min_status in _TERMINAL_STATUSES:
                        objective_deps_display = "ready"
                    else:
                        objective_deps_display = min_status.replace("_", " ")

        # Format updated_at display
        updated_display = format_relative_time(plan.updated_at.isoformat()) or "-"

        # Format created_at display
        created_display = format_relative_time(plan.created_at.isoformat()) or "-"

        # Determine if this is a learn plan
        is_learn_plan = "erk-learn" in plan.labels

        return PlanRowData(
            plan_id=plan_id,
            plan_url=plan.url,
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
            plan_body=plan.body or "",
            pr_title=pr_title,
            pr_state=pr_state,
            pr_head_branch=pr_head_branch,
            worktree_branch=worktree_branch,
            last_local_impl_at=last_local_impl_at,
            last_remote_impl_at=last_remote_impl_at,
            run_id=run_id,
            run_status=run_status,
            run_conclusion=run_conclusion,
            log_entries=log_entries,
            resolved_comment_count=resolved_comment_count,
            total_comment_count=total_comment_count,
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
            updated_at=plan.updated_at,
            updated_display=updated_display,
            created_at=plan.created_at,
            created_display=created_display,
            author=str(plan.metadata.get("author", "")),
            is_learn_plan=is_learn_plan,
        )


def _format_learn_display(
    learn_status: str | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
    *,
    learn_plan_issue_closed: bool | None,
) -> str:
    """Format learn status for display with inline descriptions.

    Args:
        learn_status: Raw status value from plan header
        learn_plan_issue: Issue number of generated learn plan
        learn_plan_pr: PR number that implemented the learn plan
        learn_plan_issue_closed: Whether the learn plan issue is closed

    Returns:
        Formatted display string based on status:
        - None or "not_started" -> "- not started"
        - "pending" -> "⟳ in progress"
        - "completed_no_plan" -> "∅ no insights"
        - "completed_with_plan" + closed -> "✅ #456" (using learn_plan_issue)
        - "completed_with_plan" + open -> "📋 #456" (using learn_plan_issue)
        - "pending_review" -> "🚧 #789" (using learn_plan_pr for draft PR)
        - "plan_completed" -> "✓ #12" (using learn_plan_pr)
    """
    if learn_status is None or learn_status == "not_started":
        return "- not started"
    if learn_status == "pending":
        return "⟳ in progress"
    if learn_status == "completed_no_plan":
        return "∅ no insights"
    if learn_status == "completed_with_plan" and learn_plan_issue is not None:
        if learn_plan_issue_closed is True:
            return f"✅ #{learn_plan_issue}"
        return f"📋 #{learn_plan_issue}"
    if learn_status == "pending_review" and learn_plan_pr is not None:
        return f"🚧 #{learn_plan_pr}"
    if learn_status == "plan_completed" and learn_plan_pr is not None:
        return f"✓ #{learn_plan_pr}"
    # Fallback for unknown status
    return "- not started"


def _format_learn_display_icon(
    learn_status: str | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
    *,
    learn_plan_issue_closed: bool | None,
) -> str:
    """Format learn status as icon-only for table display.

    Args:
        learn_status: Raw status value from plan header
        learn_plan_issue: Issue number of generated learn plan
        learn_plan_pr: PR number that implemented the learn plan
        learn_plan_issue_closed: Whether the learn plan issue is closed

    Returns:
        Icon-only display string based on status:
        - None or "not_started" -> "-"
        - "pending" -> "⟳"
        - "completed_no_plan" -> "∅"
        - "completed_with_plan" + closed -> "✅ #456" (using learn_plan_issue)
        - "completed_with_plan" + open -> "📋 #456" (using learn_plan_issue)
        - "pending_review" -> "🚧 #789" (using learn_plan_pr for draft PR)
        - "plan_completed" -> "✓ #12" (using learn_plan_pr)
    """
    if learn_status is None or learn_status == "not_started":
        return "-"
    if learn_status == "pending":
        return "⟳"
    if learn_status == "completed_no_plan":
        return "∅"
    if learn_status == "completed_with_plan" and learn_plan_issue is not None:
        if learn_plan_issue_closed is True:
            return f"✅ #{learn_plan_issue}"
        return f"📋 #{learn_plan_issue}"
    if learn_status == "pending_review" and learn_plan_pr is not None:
        return f"🚧 #{learn_plan_pr}"
    if learn_status == "plan_completed" and learn_plan_pr is not None:
        return f"✓ #{learn_plan_pr}"
    # Fallback for unknown status
    return "-"


def _ensure_erk_metadata_dir_from_context(repo: RepoContext | NoRepoSentinel) -> None:
    """Ensure erk metadata directory exists, handling sentinel case."""
    if isinstance(repo, RepoContext):
        ensure_erk_metadata_dir(repo)
