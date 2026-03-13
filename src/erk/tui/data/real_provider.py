"""Real implementation of PrDataProvider for TUI data assembly."""

import logging
from datetime import UTC, datetime

from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_relative_time,
    format_submission_time,
    format_workflow_outcome,
    format_workflow_run_id,
    get_workflow_run_state,
    strip_rich_markup,
)
from erk.core.pr_utils import select_display_pr
from erk.core.repo_discovery import NoRepoSentinel, RepoContext, ensure_erk_metadata_dir
from erk.tui.data.provider_abc import PrDataProvider
from erk.tui.data.types import FetchTimings, PrFilters, PrRowData, RunRowData
from erk.tui.sorting.types import BranchActivity
from erk_shared.gateway.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.gateway.github.metadata.core import (
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
    CI_SUMMARY_COMMENT_ID,
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
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.http.abc import HttpClient
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


class RealPrDataProvider(PrDataProvider):
    """Production implementation that assembles TUI display data.

    Transforms PlanListData into PrRowData for TUI display.
    Domain operations (close_pr, dispatch, etc.) are on PrService.
    """

    def __init__(
        self,
        ctx: ErkContext,
        *,
        location: GitHubRepoLocation,
        http_client: HttpClient,
    ) -> None:
        """Initialize with context and repository info.

        Args:
            ctx: ErkContext with all dependencies
            location: GitHub repository location (local root + repo identity)
            http_client: HTTP client for direct API calls (faster than subprocess)
        """
        self._ctx = ctx
        self._location = location
        self._http_client = http_client

    def fetch_prs(self, filters: PrFilters) -> tuple[list[PrRowData], FetchTimings | None]:
        """Fetch plans and transform to TUI row format.

        Args:
            filters: Filter options for the query

        Returns:
            Tuple of (list of PrRowData for display, optional FetchTimings breakdown)
        """
        t_total_start = self._ctx.time.monotonic()

        # Determine if we need workflow runs
        needs_workflow_runs = filters.show_runs or filters.run_state is not None

        # Route to the appropriate service based on the view's labels
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
        worktree_by_pr_number = self._build_worktree_mapping()
        t_wt_end = self._ctx.time.monotonic()

        plans = plan_data.plans

        # Transform to PrRowData
        t_rows_start = self._ctx.time.monotonic()
        rows: list[PrRowData] = []
        global_config = self._ctx.global_config
        use_graphite = global_config.use_graphite if global_config is not None else False

        for plan in plans:
            pr_number = int(plan.pr_identifier)

            workflow_run = plan_data.workflow_runs.get(pr_number)

            if filters.run_state is not None:
                if workflow_run is None:
                    continue
                if get_workflow_run_state(workflow_run) != filters.run_state:
                    continue

            row = self._build_row_data(
                plan=plan,
                pr_number=pr_number,
                pr_linkages=plan_data.pr_linkages,
                workflow_run=workflow_run,
                worktree_by_pr_number=worktree_by_pr_number,
                use_graphite=use_graphite,
            )
            rows.append(row)
        t_rows_end = self._ctx.time.monotonic()

        timings = FetchTimings(
            rest_issues_ms=plan_data.api_ms,
            graphql_enrich_ms=0.0,
            pr_parsing_ms=plan_data.plan_parsing_ms,
            workflow_runs_ms=plan_data.workflow_runs_ms,
            worktree_mapping_ms=(t_wt_end - t_wt_start) * 1000,
            row_building_ms=(t_rows_end - t_rows_start) * 1000,
            total_ms=(t_rows_end - t_total_start) * 1000,
            warnings=plan_data.warnings,
        )

        logger.info("fetch_prs timings: %s", timings.summary())
        self._append_timing_log(timings, len(rows))

        return (rows, timings)

    def fetch_runs(self) -> list[RunRowData]:
        """Fetch workflow runs for the Runs tab.

        Ports logic from erk.cli.commands.run.list_cmd._list_runs().

        Returns:
            List of RunRowData for display, sorted by created_at descending
        """
        # Lazy import to avoid circular dependency through erk.cli.commands.run.__init__
        from concurrent.futures import ThreadPoolExecutor

        from erk.cli.commands.run.shared import extract_pr_number

        _PER_WORKFLOW_LIMIT = 20
        _MAX_DISPLAY_RUNS = 50
        _MAX_TITLE_LENGTH = 50
        _MAX_BRANCH_LENGTH = 40

        # 1. Fetch workflow runs from each registered workflow in parallel
        #    Per-workflow queries return only erk runs (not CI/lint noise).
        #    Filter by current user so multi-contributor repos show only your runs.
        _, gh_username, _ = self._ctx.github.check_auth_status()
        tagged_runs: list[tuple[WorkflowRun, str]] = []

        def _fetch_workflow(cmd_name: str, workflow_file: str) -> list[tuple[WorkflowRun, str]]:
            runs = self._ctx.github.list_workflow_runs(
                self._location.root, workflow_file, _PER_WORKFLOW_LIMIT, user=gh_username
            )
            return [(run, cmd_name) for run in runs]

        with ThreadPoolExecutor(max_workers=len(WORKFLOW_COMMAND_MAP)) as executor:
            futures = {
                executor.submit(_fetch_workflow, cmd_name, workflow_file): cmd_name
                for cmd_name, workflow_file in WORKFLOW_COMMAND_MAP.items()
            }
            for future in futures:
                tagged_runs.extend(future.result())

        # Sort by created_at descending
        tagged_runs.sort(
            key=lambda pair: pair[0].created_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        tagged_runs = tagged_runs[:_MAX_DISPLAY_RUNS]

        if not tagged_runs:
            return []

        # 2. Extract PR numbers from display_titles
        run_pr_numbers: dict[str, int] = {}

        for run, _workflow_name in tagged_runs:
            pr_num = extract_pr_number(run.display_title)
            if pr_num is not None:
                run_pr_numbers[run.run_id] = pr_num

        # 3. Fetch direct PR info
        pr_info_map: dict[int, PullRequestInfo] = {}
        direct_pr_numbers = set(run_pr_numbers.values())
        if direct_pr_numbers:
            pr_info_map = self._ctx.github.get_prs_by_numbers(
                self._location, list(direct_pr_numbers)
            )

        use_graphite = self._ctx.global_config.use_graphite if self._ctx.global_config else False

        # 6. Build RunRowData for each run
        rows: list[RunRowData] = []
        for run, workflow_name in tagged_runs:
            pr_num = run_pr_numbers.get(run.run_id)

            # Format run-id with link
            workflow_url = (
                f"https://github.com/{self._location.repo_id.owner}/"
                f"{self._location.repo_id.repo}/actions/runs/{run.run_id}"
            )
            run_id_display = strip_rich_markup(format_workflow_run_id(run, workflow_url))

            # Format status
            status_display = strip_rich_markup(format_workflow_outcome(run))

            # Format submission time
            submitted_display = strip_rich_markup(format_submission_time(run.created_at))

            # Format PR-related columns
            pr_url: str | None = None
            pr_title: str | None = None
            pr_display = "-"
            title_display = "-"
            checks_display = "-"
            pr_state: str | None = None
            pr_status_display = "-"

            if pr_num is not None:
                pr_info = pr_info_map.get(pr_num)
                if pr_info is not None:
                    graphite_url = self._ctx.graphite.get_graphite_url(
                        GitHubRepoId(pr_info.owner, pr_info.repo), pr_info.number
                    )
                    pr_url = graphite_url if use_graphite and graphite_url else pr_info.url
                    pr_display = f"#{pr_info.number}"
                    pr_title = pr_info.title
                    title = pr_info.title or "-"
                    if len(title) > _MAX_TITLE_LENGTH:
                        title = title[: _MAX_TITLE_LENGTH - 3] + "..."
                    title_display = title
                    checks_display = strip_rich_markup(format_checks_cell(pr_info))
                    pr_state = pr_info.state
                    pr_status_display = strip_rich_markup(get_pr_status_emoji(pr_info))
                else:
                    # Have PR number but no details
                    pr_url = (
                        f"https://github.com/{self._location.repo_id.owner}/"
                        f"{self._location.repo_id.repo}/pull/{pr_num}"
                    )
                    pr_display = f"#{pr_num}"

            # Format branch column: prefer PR's head_branch (original feature branch)
            # over run.branch, which becomes "master" after merge+branch deletion
            pr_info_for_branch = pr_info_map.get(pr_num) if pr_num is not None else None
            if pr_info_for_branch is not None and pr_info_for_branch.head_branch is not None:
                branch_name = pr_info_for_branch.head_branch
            elif run.branch != "master" and run.branch != "main":
                branch_name = run.branch
            else:
                branch_name = "-"
            branch = branch_name
            if len(branch_name) > _MAX_BRANCH_LENGTH:
                branch_name = branch_name[: _MAX_BRANCH_LENGTH - 3] + "..."
            branch_display = branch_name

            rows.append(
                RunRowData(
                    run_id=run.run_id,
                    run_url=workflow_url,
                    status=run.status or "",
                    conclusion=run.conclusion,
                    status_display=status_display,
                    workflow_name=workflow_name,
                    pr_number=pr_num,
                    pr_url=pr_url,
                    pr_display=pr_display,
                    pr_title=pr_title,
                    pr_state=pr_state,
                    pr_status_display=pr_status_display,
                    title_display=title_display,
                    branch_display=branch_display,
                    submitted_display=submitted_display,
                    created_at=run.created_at,
                    checks_display=checks_display,
                    run_id_display=run_id_display,
                    branch=branch,
                )
            )
        return rows

    def fetch_branch_activity(self, rows: list[PrRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of pr_number to BranchActivity for plans with local worktrees.
        """
        result: dict[int, BranchActivity] = {}
        trunk = self._ctx.git.branch.detect_trunk_branch(self._location.root)

        for row in rows:
            if not row.exists_locally or row.worktree_branch is None:
                continue

            commits = self._ctx.git.branch.get_branch_commits_with_authors(
                self._location.root,
                row.worktree_branch,
                trunk,
                limit=1,
            )

            if commits:
                timestamp_str = commits[0]["timestamp"]
                commit_at = datetime.fromisoformat(timestamp_str)
                result[row.pr_number] = BranchActivity(
                    last_commit_at=commit_at,
                    last_commit_author=commits[0]["author"],
                )
            else:
                result[row.pr_number] = BranchActivity.empty()

        return result

    def fetch_prs_by_ids(self, pr_ids: set[int]) -> list[PrRowData]:
        """Fetch specific plans by their GitHub numbers.

        Args:
            pr_ids: Set of plan numbers to fetch (issue or PR numbers)

        Returns:
            List of PrRowData objects sorted by pr_number
        """
        if not pr_ids:
            return []

        issues, pr_linkages = self._ctx.github.get_issues_by_numbers_with_pr_linkages(
            location=self._location,
            pr_numbers=list(pr_ids),
        )

        plans = [github_issue_to_plan(issue) for issue in issues]
        worktree_by_pr_number = self._build_worktree_mapping()

        global_config = self._ctx.global_config
        use_graphite = global_config.use_graphite if global_config is not None else False
        rows: list[PrRowData] = []
        for plan in plans:
            pr_number = int(plan.pr_identifier)
            row = self._build_row_data(
                plan=plan,
                pr_number=pr_number,
                pr_linkages=pr_linkages,
                workflow_run=None,
                worktree_by_pr_number=worktree_by_pr_number,
                use_graphite=use_graphite,
            )
            rows.append(row)

        rows.sort(key=lambda r: r.pr_number)
        return rows

    def fetch_prs_for_objective(self, objective_issue: int) -> list[PrRowData]:
        """Fetch plans associated with a specific objective.

        Args:
            objective_issue: The objective issue number to filter by

        Returns:
            List of PrRowData objects for plans linked to this objective
        """
        all_plans: list[PrRowData] = []
        for state in ("open", "closed"):
            filters = PrFilters(
                labels=("erk-pr",),
                state=state,
                run_state=None,
                limit=100,
                show_prs=True,
                show_runs=False,
                exclude_labels=(),
                creator=None,
            )
            rows, _timings = self.fetch_prs(filters)
            all_plans.extend(rows)
        return [row for row in all_plans if row.objective_issue == objective_issue]

    def _append_timing_log(self, timings: FetchTimings, row_count: int) -> None:
        """Append timing data to .erk/scratch/dash-timings.log.

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

        Returns:
            Mapping of plan ID to tuple of (worktree_name, branch_name)
        """
        _ensure_erk_metadata_dir_from_context(self._ctx.repo)
        worktree_by_pr_number: dict[int, tuple[str, str | None]] = {}
        worktrees = self._ctx.git.worktree.list_worktrees(self._location.root)
        for worktree in worktrees:
            impl_dir = resolve_impl_dir(worktree.path, branch_name=worktree.branch)
            if impl_dir is None:
                continue
            plan_ref = read_plan_ref(impl_dir)
            if plan_ref is None or not plan_ref.pr_id.isdigit():
                continue
            plan_number = int(plan_ref.pr_id)
            if plan_number not in worktree_by_pr_number:
                worktree_by_pr_number[plan_number] = (
                    worktree.path.name,
                    worktree.branch,
                )
        return worktree_by_pr_number

    def _build_row_data(
        self,
        *,
        plan: Plan,
        pr_number: int,
        pr_linkages: dict[int, list[PullRequestInfo]],
        workflow_run: WorkflowRun | None,
        worktree_by_pr_number: dict[int, tuple[str, str | None]],
        use_graphite: bool,
    ) -> PrRowData:
        """Build a single PrRowData from plan and related data."""
        full_title = plan.title

        # Worktree info
        worktree_name = ""
        worktree_branch: str | None = None
        exists_locally = False

        if pr_number in worktree_by_pr_number:
            worktree_name, worktree_branch = worktree_by_pr_number[pr_number]
            exists_locally = True

        # Extract from pre-parsed header fields
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

        objective_issue = header_int(plan.header_fields, OBJECTIVE_ISSUE)

        # Extract ci_summary_comment_id from pre-parsed header fields
        ci_summary_comment_id = header_int(plan.header_fields, CI_SUMMARY_COMMENT_ID)

        learn_plan_issue_closed: bool | None = None

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

        last_local_impl_at = header_datetime(plan.header_fields, LAST_LOCAL_IMPL_AT)
        last_remote_impl_at = header_datetime(plan.header_fields, LAST_REMOTE_IMPL_AT)

        local_impl = format_relative_time(local_impl_str)
        local_impl_display = local_impl if local_impl else "-"
        remote_impl = format_relative_time(remote_impl_str)
        remote_impl_display = remote_impl if remote_impl else "-"

        # PR info — pr_url defaults to the issue URL, overridden by linked PR URL
        pr_url: str | None = plan.url
        pr_title: str | None = None
        pr_state: str | None = None
        pr_head_branch: str | None = None
        pr_display = "-"
        checks_display = "-"

        resolved_comment_count = 0
        total_comment_count = 0
        comments_display = "-"

        pr_is_draft: bool | None = None
        pr_has_conflicts: bool | None = None
        pr_review_decision: str | None = None
        pr_checks_passing: bool | None = None
        pr_checks_counts: tuple[int, int] | None = None
        pr_has_unresolved_comments: bool | None = None
        pr_is_stacked: bool | None = None

        if pr_number in pr_linkages:
            issue_prs = pr_linkages[pr_number]
            selected_pr = select_display_pr(issue_prs, exclude_pr_numbers=None)
            if selected_pr is not None:
                pr_title = selected_pr.title
                pr_state = selected_pr.state
                pr_head_branch = selected_pr.head_branch
                graphite_url = self._ctx.graphite.get_graphite_url(
                    GitHubRepoId(selected_pr.owner, selected_pr.repo), selected_pr.number
                )
                pr_url = graphite_url if use_graphite and graphite_url else selected_pr.url
                emoji = get_pr_status_emoji(selected_pr)
                pr_display = f"#{selected_pr.number} {emoji}"
                checks_display = format_checks_cell(selected_pr)

                pr_is_draft = selected_pr.is_draft
                pr_has_conflicts = selected_pr.has_conflicts
                pr_review_decision = selected_pr.review_decision
                pr_checks_passing = selected_pr.checks_passing
                pr_checks_counts = selected_pr.checks_counts
                if pr_head_branch is not None:
                    parent = self._ctx.branch_manager.get_parent_branch(
                        self._location.root, pr_head_branch
                    )
                    if parent is not None:
                        pr_is_stacked = parent not in ("master", "main")

                if pr_is_stacked is None and selected_pr.base_ref_name is not None:
                    pr_is_stacked = selected_pr.base_ref_name not in ("master", "main")

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

        log_entries: tuple[tuple[str, str, str], ...] = ()

        learn_run_url: str | None = None
        if learn_run_id is not None and plan.url is not None:
            parts = plan.url.split("/")
            if len(parts) >= 5:
                owner = parts[-4]
                repo_name = parts[-3]
                learn_run_url = (
                    f"https://github.com/{owner}/{repo_name}/actions/runs/{learn_run_id}"
                )

        objective_url = (
            f"https://github.com/{self._location.repo_id.owner}/{self._location.repo_id.repo}/issues/{objective_issue}"
            if objective_issue is not None
            else None
        )
        objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

        objective_slug_display = "-"
        if plan.body:
            slug = extract_objective_slug(plan.body)
            if slug is not None:
                objective_slug_display = slug[:25]
            elif plan.title:
                stripped = plan.title.removeprefix("Objective: ")
                objective_slug_display = stripped[:25]

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

                    target = next((n for n in graph.nodes if n.id == next_node["id"]), None)
                    if target is not None and target.depends_on:
                        node_map = {n.id: n for n in graph.nodes}
                        for dep_id in target.depends_on:
                            if dep_id in node_map:
                                dep = node_map[dep_id]
                                if dep.status not in _TERMINAL_STATUSES and dep.pr is not None:
                                    num = dep.pr.lstrip("#")
                                    repo_id = self._location.repo_id
                                    url = f"https://github.com/{repo_id.owner}/{repo_id.repo}/pull/{num}"
                                    objective_deps_plans.append((dep.pr, url))

                    if (
                        target is not None
                        and target.pr is not None
                        and target.status not in _TERMINAL_STATUSES
                    ):
                        existing_prs = {pr_ref for pr_ref, _ in objective_deps_plans}
                        if target.pr not in existing_prs:
                            num = target.pr.lstrip("#")
                            repo_id = self._location.repo_id
                            url = f"https://github.com/{repo_id.owner}/{repo_id.repo}/pull/{num}"
                            objective_deps_plans.append((target.pr, url))

        updated_display = format_relative_time(plan.updated_at.isoformat()) or "-"
        created_display = format_relative_time(plan.created_at.isoformat()) or "-"
        is_learn_plan = "erk-learn" in plan.labels

        lifecycle_display = _compute_lifecycle_display(
            plan, has_workflow_run=workflow_run is not None, linked_pr_state=pr_state
        )

        status_display = compute_status_indicators(
            lifecycle_display,
            is_draft=pr_is_draft,
            has_conflicts=pr_has_conflicts,
            review_decision=pr_review_decision,
            checks_passing=pr_checks_passing,
            has_unresolved_comments=pr_has_unresolved_comments,
            is_stacked=pr_is_stacked,
        )

        return PrRowData(
            pr_number=pr_number,
            pr_url=pr_url,
            pr_display=pr_display,
            checks_display=checks_display,
            checks_passing=pr_checks_passing,
            checks_counts=pr_checks_counts,
            ci_summary_comment_id=ci_summary_comment_id,
            worktree_name=worktree_name,
            exists_locally=exists_locally,
            local_impl_display=local_impl_display,
            remote_impl_display=remote_impl_display,
            run_id_display=run_id_display,
            run_state_display=run_state_display,
            run_url=run_url,
            full_title=full_title,
            pr_body=plan.body or "",
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
    """Format learn status for display with inline descriptions."""
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
    return "- not started"


def _format_learn_display_icon(
    learn_status: str | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
    *,
    learn_plan_issue_closed: bool | None,
) -> str:
    """Format learn status as icon-only for table display."""
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
    return "-"


def _compute_lifecycle_display(
    plan: Plan, *, has_workflow_run: bool, linked_pr_state: str | None
) -> str:
    """Compute lifecycle stage display string for a plan."""
    from erk_shared.gateway.plan_data_provider.lifecycle import compute_lifecycle_display

    return compute_lifecycle_display(
        plan, has_workflow_run=has_workflow_run, linked_pr_state=linked_pr_state
    )


def _ensure_erk_metadata_dir_from_context(repo: RepoContext | NoRepoSentinel) -> None:
    """Ensure erk metadata directory exists, handling sentinel case."""
    if isinstance(repo, RepoContext):
        ensure_erk_metadata_dir(repo)
