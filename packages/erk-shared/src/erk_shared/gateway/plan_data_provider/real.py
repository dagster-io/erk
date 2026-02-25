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
from erk.tui.data.types import FetchTimings, PlanFilters, PlanRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.ci_summary_parsing import parse_ci_summaries
from erk_shared.gateway.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.gateway.github.metadata.core import (
    extract_objective_from_comment,
    extract_objective_header_comment_id,
    extract_objective_slug,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    _TERMINAL_STATUSES,
    build_graph,
    build_state_sparkline,
    compute_graph_summary,
    find_graph_next_node,
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
    WORKTREE_NAME,
)
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRCheckRun,
    PRNotFound,
    PRReviewThread,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.http.abc import HttpClient
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider
from erk_shared.gateway.plan_data_provider.lifecycle import compute_status_indicators
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir
from erk_shared.plan_store.conversion import (
    github_issue_to_plan,
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

    def fetch_plans(self, filters: PlanFilters) -> tuple[list[PlanRowData], FetchTimings | None]:
        """Fetch plans and transform to TUI row format.

        Args:
            filters: Filter options for the query

        Returns:
            Tuple of (list of PlanRowData for display, optional FetchTimings breakdown)
        """
        t_total_start = self._ctx.time.monotonic()

        # Determine if we need workflow runs
        needs_workflow_runs = filters.show_runs or filters.run_state is not None

        # Route to the appropriate service based on the view's labels
        # Objectives have their own dedicated service; all other queries
        # (plans, learn plans, custom label combos) use the plan list service.
        if "erk-objective" in filters.labels:
            plan_data = self._ctx.objective_list_service.get_objective_list_data(
                location=self._location,
                state=filters.state,
                limit=filters.limit,
                skip_workflow_runs=not needs_workflow_runs,
                creator=filters.creator,
                exclude_labels=list(filters.exclude_labels) if filters.exclude_labels else None,
                http_client=self._http_client,
            )
        else:
            plan_data = self._ctx.plan_list_service.get_plan_list_data(
                location=self._location,
                labels=list(filters.labels),
                state=filters.state,
                limit=filters.limit,
                skip_workflow_runs=not needs_workflow_runs,
                creator=filters.creator,
                exclude_labels=list(filters.exclude_labels) if filters.exclude_labels else None,
                http_client=self._http_client,
            )

        # Build local worktree mapping
        t_wt_start = self._ctx.time.monotonic()
        worktree_by_plan_id = self._build_worktree_mapping()
        t_wt_end = self._ctx.time.monotonic()

        # Use pre-converted Plan objects from PlanListData
        plans = plan_data.plans

        # Transform to PlanRowData
        t_rows_start = self._ctx.time.monotonic()
        rows: list[PlanRowData] = []
        global_config = self._ctx.global_config
        use_graphite = global_config.use_graphite if global_config is not None else False

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
            )
            rows.append(row)
        t_rows_end = self._ctx.time.monotonic()

        # Build timing breakdown
        # api_ms covers REST + GraphQL enrichment from PlanListData
        # plan_parsing_ms covers body parsing from PlanListData
        # workflow_runs_ms covers workflow run fetching from PlanListData
        timings = FetchTimings(
            rest_issues_ms=plan_data.api_ms,
            graphql_enrich_ms=0.0,
            plan_parsing_ms=plan_data.plan_parsing_ms,
            workflow_runs_ms=plan_data.workflow_runs_ms,
            worktree_mapping_ms=(t_wt_end - t_wt_start) * 1000,
            row_building_ms=(t_rows_end - t_rows_start) * 1000,
            total_ms=(t_rows_end - t_total_start) * 1000,
            warnings=plan_data.warnings,
        )

        logger.info("fetch_plans timings: %s", timings.summary())

        # Write timing to log file for post-execution analysis
        self._append_timing_log(timings, len(rows))

        return (rows, timings)

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

    def dispatch_to_queue(self, plan_id: int, plan_url: str) -> None:
        """Dispatch a plan to the implementation queue.

        Runs 'erk pr dispatch' as a subprocess to handle the complex workflow
        of creating branches, PRs, and triggering GitHub Actions.

        Args:
            plan_id: The plan ID to dispatch
            plan_url: The plan URL (unused, kept for interface consistency)
        """
        # Run erk pr dispatch command from the repository root
        # -f flag prevents blocking on existing branch prompts in TUI context
        subprocess.run(
            ["erk", "pr", "dispatch", str(plan_id), "-f"],
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
        """Return plan content from the PR body.

        Plans are PR-based: plan_body is the already-extracted content from
        PlannedPRPlanListService. Return it directly.

        Args:
            plan_id: The GitHub PR number
            plan_body: The extracted plan content from the PR body

        Returns:
            The plan content, or None if empty
        """
        return plan_body if plan_body.strip() else None

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

    def fetch_plans_by_ids(self, plan_ids: set[int]) -> list[PlanRowData]:
        """Fetch specific plans by their GitHub numbers.

        Uses get_issues_by_numbers_with_pr_linkages (backed by the
        issueOrPullRequest GraphQL query) for targeted fetching. Works
        for both issue-backed and PR-backed plans.

        Args:
            plan_ids: Set of plan numbers to fetch (issue or PR numbers)

        Returns:
            List of PlanRowData objects sorted by plan_id
        """
        if not plan_ids:
            return []

        issues, pr_linkages = self._ctx.github.get_issues_by_numbers_with_pr_linkages(
            location=self._location,
            plan_numbers=list(plan_ids),
        )

        # Convert IssueInfo -> Plan
        plans = [github_issue_to_plan(issue) for issue in issues]

        # Build worktree mapping
        worktree_by_plan_id = self._build_worktree_mapping()

        # Build row data
        global_config = self._ctx.global_config
        use_graphite = global_config.use_graphite if global_config is not None else False
        rows: list[PlanRowData] = []
        for plan in plans:
            plan_id = int(plan.plan_identifier)
            row = self._build_row_data(
                plan=plan,
                plan_id=plan_id,
                pr_linkages=pr_linkages,
                workflow_run=None,
                worktree_by_plan_id=worktree_by_plan_id,
                use_graphite=use_graphite,
            )
            rows.append(row)

        rows.sort(key=lambda r: r.plan_id)
        return rows

    def fetch_plans_for_objective(self, objective_issue: int) -> list[PlanRowData]:
        """Fetch plans associated with a specific objective.

        Fetches erk-plan issues in both open and closed states, then filters
        client-side by objective_issue.

        Args:
            objective_issue: The objective issue number to filter by

        Returns:
            List of PlanRowData objects for plans linked to this objective
        """
        all_plans: list[PlanRowData] = []
        for state in ("open", "closed"):
            filters = PlanFilters(
                labels=("erk-plan",),
                state=state,
                run_state=None,
                limit=100,
                show_prs=True,
                show_runs=False,
                exclude_labels=(),
                creator=None,
            )
            rows, _timings = self.fetch_plans(filters)
            all_plans.extend(rows)
        return [row for row in all_plans if row.objective_issue == objective_issue]

    def get_branch_stack(self, branch: str) -> list[str] | None:
        """Get the Graphite stack containing a branch.

        Delegates to BranchManager which reads local Graphite cache (no network).

        Args:
            branch: The branch name to look up

        Returns:
            Ordered list of branch names in the stack, or None
        """
        return self._ctx.branch_manager.get_branch_stack(self._location.root, branch)

    def fetch_check_runs(self, pr_number: int) -> list[PRCheckRun]:
        """Fetch failing check runs for a pull request.

        Args:
            pr_number: The PR number to fetch check runs for

        Returns:
            List of PRCheckRun for failing checks, sorted by name
        """
        return self._ctx.github.get_pr_check_runs(self._location.root, pr_number)

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

    def fetch_ci_summaries(self, pr_number: int) -> dict[str, str]:
        """Fetch CI failure summaries for a pull request.

        Finds the latest CI workflow run for this PR's head branch,
        looks for a ci-summarize job, and parses its log markers.

        Args:
            pr_number: The PR number to fetch summaries for

        Returns:
            Mapping of check name to summary text, or empty dict
        """
        # Get PR details to find head branch
        pr_result = self._ctx.github.get_pr(self._location.root, pr_number)
        if isinstance(pr_result, PRNotFound):
            return {}

        # Find CI workflow runs for this PR's head branch
        runs_by_branch = self._ctx.github.get_workflow_runs_by_branches(
            self._location.root, "ci.yml", [pr_result.head_ref_name]
        )
        run = runs_by_branch.get(pr_result.head_ref_name)
        if run is None:
            return {}

        # Fetch ci-summarize job logs
        log_text = self._ctx.github.get_ci_summary_logs(self._location.root, str(run.run_id))
        if log_text is None:
            return {}

        return parse_ci_summaries(log_text)

    def _append_timing_log(self, timings: FetchTimings, row_count: int) -> None:
        """Append timing data to .erk/scratch/dash-timings.log for post-execution analysis.

        Silently ignores all errors (sentinel paths in tests, missing directory,
        permissions, etc.) since timing logs are strictly informational.

        Args:
            timings: Timing breakdown for this fetch cycle
            row_count: Number of rows returned
        """
        try:
            log_dir = self._location.root / ".erk" / "scratch"
            if not log_dir.is_dir():
                return
            log_file = log_dir / "dash-timings.log"
            timestamp = self._ctx.time.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"{timestamp}  rows={row_count}  {timings.summary()}\n"
            with open(log_file, "a") as f:
                f.write(line)
        except Exception:
            logger.debug("Failed to write timing log", exc_info=True)

    def _build_worktree_mapping(self) -> dict[int, tuple[str, str | None]]:
        """Build mapping of plan ID to (worktree name, branch).

        Uses resolve_impl_dir() for unified discovery of implementation folders
        (both legacy .impl/ and branch-scoped .erk/impl-context/).
        Plan-ref.json is the sole source of truth for plan-to-branch mapping.

        Returns:
            Mapping of plan ID to tuple of (worktree_name, branch_name)
        """
        _ensure_erk_metadata_dir_from_context(self._ctx.repo)
        worktree_by_plan_id: dict[int, tuple[str, str | None]] = {}
        worktrees = self._ctx.git.worktree.list_worktrees(self._location.root)
        for worktree in worktrees:
            impl_dir = resolve_impl_dir(worktree.path, branch_name=worktree.branch)
            if impl_dir is None:
                continue
            plan_ref = read_plan_ref(impl_dir)
            if plan_ref is None or not plan_ref.plan_id.isdigit():
                continue
            plan_number = int(plan_ref.plan_id)
            if plan_number not in worktree_by_plan_id:
                worktree_by_plan_id[plan_number] = (
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
    ) -> PlanRowData:
        """Build a single PlanRowData from plan and related data."""
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

        # Extract objective_issue from pre-parsed header fields
        objective_issue = header_int(plan.header_fields, OBJECTIVE_ISSUE)

        # Learn plan issue closed state is not fetched (too slow for N sequential calls).
        # Falls back to open icon (📋) which is acceptable.
        learn_plan_issue_closed: bool | None = None

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

        # PR status fields for lifecycle enrichment
        pr_is_draft: bool | None = None
        pr_has_conflicts: bool | None = None
        pr_review_decision: str | None = None
        pr_checks_passing: bool | None = None
        pr_checks_counts: tuple[int, int] | None = None
        pr_has_unresolved_comments: bool | None = None
        pr_is_stacked: bool | None = None

        if plan_id in pr_linkages:
            issue_prs = pr_linkages[plan_id]
            selected_pr = select_display_pr(issue_prs, exclude_pr_numbers=None)
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

                # Extract status fields for lifecycle enrichment
                pr_is_draft = selected_pr.is_draft
                pr_has_conflicts = selected_pr.has_conflicts
                pr_review_decision = selected_pr.review_decision
                pr_checks_passing = selected_pr.checks_passing
                pr_checks_counts = selected_pr.checks_counts
                # Check Graphite local parent first (authoritative when available)
                if pr_head_branch is not None:
                    parent = self._ctx.branch_manager.get_parent_branch(
                        self._location.root, pr_head_branch
                    )
                    if parent is not None:
                        pr_is_stacked = parent not in ("master", "main")

                # Fall back to GitHub base_ref_name when branch not tracked by Graphite
                if pr_is_stacked is None and selected_pr.base_ref_name is not None:
                    pr_is_stacked = selected_pr.base_ref_name not in ("master", "main")

                # Get review thread counts from batched PR data
                if selected_pr.review_thread_counts is not None:
                    resolved_comment_count, total_comment_count = selected_pr.review_thread_counts
                    comments_display = f"{resolved_comment_count}/{total_comment_count}"
                    pr_has_unresolved_comments = total_comment_count > resolved_comment_count
                else:
                    comments_display = "0/0"
                    pr_has_unresolved_comments = False

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
        objective_url = (
            f"https://github.com/{self._location.repo_id.owner}/{self._location.repo_id.repo}/issues/{objective_issue}"
            if objective_issue is not None
            else None
        )
        objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

        # Compute slug display
        objective_slug_display = "-"
        if plan.body:
            slug = extract_objective_slug(plan.body)
            if slug is not None:
                objective_slug_display = slug[:25]
            elif plan.title:
                stripped = plan.title.removeprefix("Objective: ")
                objective_slug_display = stripped[:25]

        # Parse roadmap for objective-specific fields
        objective_done_nodes = 0
        objective_total_nodes = 0
        objective_progress_display = "-"
        objective_state_display = "-"
        objective_deps_display = "-"
        objective_next_node_display = "-"
        objective_deps_plans: list[tuple[str, str]] = []
        if plan.body:
            phases, _errors = parse_roadmap(plan.body)
            if phases:
                graph = build_graph(phases)
                summary = compute_graph_summary(graph)
                objective_done_nodes = summary["done"]
                objective_total_nodes = summary["total_nodes"]
                objective_progress_display = f"{objective_done_nodes}/{objective_total_nodes}"
                objective_state_display = build_state_sparkline(graph.nodes)
                next_node = find_graph_next_node(graph, phases)
                if next_node is not None:
                    objective_next_node_display = next_node["id"]
                    min_status = graph.min_dep_status(next_node["id"])
                    if min_status is None or min_status in _TERMINAL_STATUSES:
                        objective_deps_display = "ready"
                    else:
                        objective_deps_display = min_status.replace("_", " ")

                    # Collect blocking dep PR numbers for the next node
                    target = next((n for n in graph.nodes if n.id == next_node["id"]), None)
                    if target is not None and target.depends_on:
                        node_map = {n.id: n for n in graph.nodes}
                        for dep_id in target.depends_on:
                            if dep_id in node_map:
                                dep = node_map[dep_id]
                                if dep.status not in _TERMINAL_STATUSES and dep.pr is not None:
                                    num = dep.pr.lstrip("#")
                                    repo_id = self._location.repo_id
                                    url = f"https://github.com/{repo_id.owner}/{repo_id.repo}/issues/{num}"
                                    objective_deps_plans.append((dep.pr, url))

                    # Also show the next node's own PR if it has one (active work indicator)
                    if (
                        target is not None
                        and target.pr is not None
                        and target.status not in _TERMINAL_STATUSES
                    ):
                        existing_prs = {pr_ref for pr_ref, _ in objective_head_plans}
                        if target.pr not in existing_prs:
                            num = target.pr.lstrip("#")
                            repo_id = self._location.repo_id
                            url = f"https://github.com/{repo_id.owner}/{repo_id.repo}/pull/{num}"
                            objective_head_plans.append((target.pr, url))

        # Format updated_at display
        updated_display = format_relative_time(plan.updated_at.isoformat()) or "-"

        # Format created_at display
        created_display = format_relative_time(plan.created_at.isoformat()) or "-"

        # Determine if this is a learn plan
        is_learn_plan = "erk-learn" in plan.labels

        # Compute lifecycle display from header or infer from metadata
        lifecycle_display = _compute_lifecycle_display(
            plan, has_workflow_run=workflow_run is not None
        )

        # Compute status indicators separately for the "sts" column
        status_display = compute_status_indicators(
            lifecycle_display,
            is_draft=pr_is_draft,
            has_conflicts=pr_has_conflicts,
            review_decision=pr_review_decision,
            checks_passing=pr_checks_passing,
            has_unresolved_comments=pr_has_unresolved_comments,
            is_stacked=pr_is_stacked,
        )

        return PlanRowData(
            plan_id=plan_id,
            plan_url=plan.url,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_display=pr_display,
            checks_display=checks_display,
            checks_passing=pr_checks_passing,
            checks_counts=pr_checks_counts,
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
            objective_url=objective_url,
            objective_display=objective_display,
            objective_done_nodes=objective_done_nodes,
            objective_total_nodes=objective_total_nodes,
            objective_progress_display=objective_progress_display,
            objective_slug_display=objective_slug_display,
            objective_state_display=objective_state_display,
            objective_deps_display=objective_deps_display,
            objective_deps_plans=tuple(objective_deps_plans),
            objective_next_node_display=objective_next_node_display,
            updated_at=plan.updated_at,
            updated_display=updated_display,
            created_at=plan.created_at,
            created_display=created_display,
            author=str(plan.metadata.get("author", "")),
            is_learn_plan=is_learn_plan,
            lifecycle_display=lifecycle_display,
            status_display=status_display,
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


def _compute_lifecycle_display(plan: Plan, *, has_workflow_run: bool) -> str:
    """Compute lifecycle stage display string for a plan.

    Delegates to lifecycle.compute_lifecycle_display. This wrapper preserves
    the module-private name used by callers within this file.
    """
    from erk_shared.gateway.plan_data_provider.lifecycle import compute_lifecycle_display

    return compute_lifecycle_display(plan, has_workflow_run=has_workflow_run)


def _ensure_erk_metadata_dir_from_context(repo: RepoContext | NoRepoSentinel) -> None:
    """Ensure erk metadata directory exists, handling sentinel case."""
    if isinstance(repo, RepoContext):
        ensure_erk_metadata_dir(repo)
