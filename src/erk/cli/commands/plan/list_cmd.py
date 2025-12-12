"""Command to list plans with filtering."""

from collections.abc import Callable
from datetime import datetime
from typing import ParamSpec, TypeVar

import click
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display import LiveDisplay
from erk.core.display_utils import (
    format_relative_time,
    format_workflow_outcome,
    format_workflow_run_id,
    get_workflow_run_state,
)
from erk.core.pr_utils import select_display_pr
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.tui.app import ErkDashApp
from erk.tui.data.provider import RealPlanDataProvider
from erk.tui.data.types import PlanFilters
from erk.tui.sorting.types import SortKey, SortState
from erk_shared.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata import (
    extract_plan_header_local_impl_at,
    extract_plan_header_local_impl_event,
    extract_plan_header_remote_impl_at,
    extract_plan_header_worktree_name,
)
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation, PullRequestInfo
from erk_shared.impl_folder import read_issue_reference
from erk_shared.integrations.browser.real import RealBrowserLauncher
from erk_shared.integrations.clipboard.real import RealClipboard
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan, PlanState

P = ParamSpec("P")
T = TypeVar("T")


def _issue_to_plan(issue: IssueInfo) -> Plan:
    """Convert IssueInfo to Plan format.

    Args:
        issue: IssueInfo from GraphQL query

    Returns:
        Plan object with equivalent data
    """
    # Map issue state to PlanState
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


def format_pr_cell(pr: PullRequestInfo, *, use_graphite: bool, graphite_url: str | None) -> str:
    """Format PR cell with clickable link and emoji: #123 👀 or #123 👀🔗

    The 🔗 emoji is appended for PRs that will auto-close the linked issue when merged.

    Args:
        pr: PR information
        use_graphite: If True, use Graphite URL; if False, use GitHub URL
        graphite_url: Graphite URL for the PR (None if unavailable)

    Returns:
        Formatted string for table cell with OSC 8 hyperlink
    """
    emoji = get_pr_status_emoji(pr)
    pr_text = f"#{pr.number}"

    # Append 🔗 for PRs that will close the issue when merged
    if pr.will_close_target:
        emoji += "🔗"

    # Determine which URL to use
    url = graphite_url if use_graphite else pr.url

    # Make PR number clickable if URL is available
    # Rich supports OSC 8 via [link=...] markup
    if url:
        return f"[link={url}]{pr_text}[/link] {emoji}"
    else:
        return f"{pr_text} {emoji}"


def format_worktree_name_cell(worktree_name: str, exists_locally: bool) -> str:
    """Format worktree name with existence styling.

    Args:
        worktree_name: Name of the worktree
        exists_locally: Whether the worktree exists on the local machine

    Returns:
        Formatted string with Rich markup:
        - Exists locally: "[yellow]name[/yellow]"
        - Doesn't exist: "-"
    """
    if not exists_locally:
        return "-"
    return f"[yellow]{worktree_name}[/yellow]"


def format_local_run_cell(
    last_local_impl_at: str | None,
    last_local_impl_event: str | None,
) -> str:
    """Format last local implementation event as relative time with indicator.

    Args:
        last_local_impl_at: ISO timestamp of last local implementation, or None
        last_local_impl_event: Event type ("started" or "ended"), or None

    Returns:
        Relative time string with event indicator (e.g., "⟳ 2h" or "✓ 2h") or "-" if no timestamp
    """
    relative_time = format_relative_time(last_local_impl_at)
    if not relative_time:
        return "-"

    # Add event indicator
    if last_local_impl_event == "started":
        return f"⟳ {relative_time}"
    if last_local_impl_event == "ended":
        return f"✓ {relative_time}"

    # Fallback for missing event (backward compatibility)
    return relative_time


def format_remote_run_cell(last_remote_impl_at: str | None) -> str:
    """Format last remote implementation timestamp as relative time.

    Args:
        last_remote_impl_at: ISO timestamp of last remote (GitHub Actions) implementation, or None

    Returns:
        Relative time string (e.g., "2h ago") or "-" if no timestamp
    """
    relative_time = format_relative_time(last_remote_impl_at)
    return relative_time if relative_time else "-"


def plan_filter_options(f: Callable[P, T]) -> Callable[P, T]:
    """Shared filter options for plan list commands."""
    f = click.option(
        "--label",
        multiple=True,
        help="Filter by label (can be specified multiple times for AND logic)",
    )(f)
    f = click.option(
        "--state",
        type=click.Choice(["open", "closed"], case_sensitive=False),
        help="Filter by state",
    )(f)
    f = click.option(
        "--run-state",
        type=click.Choice(
            ["queued", "in_progress", "success", "failure", "cancelled"], case_sensitive=False
        ),
        help="Filter by workflow run state",
    )(f)
    f = click.option(
        "--limit",
        type=int,
        help="Maximum number of results to return",
    )(f)
    f = click.option(
        "--all-users",
        "-A",
        is_flag=True,
        default=False,
        help="Show plans from all users (default: show only your plans)",
    )(f)
    f = click.option(
        "--sort",
        type=click.Choice(["issue", "activity"], case_sensitive=False),
        default="issue",
        help="Sort order: by issue number (default) or recent branch activity",
    )(f)
    return f


def dash_options(f: Callable[P, T]) -> Callable[P, T]:
    """TUI-specific options for dash command."""
    f = click.option(
        "--interval",
        type=float,
        default=15.0,
        help="Refresh interval in seconds (default: 15.0)",
    )(f)
    f = click.option(
        "--sort",
        type=click.Choice(["issue", "activity"], case_sensitive=False),
        default="issue",
        help="Sort order: by issue number (default) or recent branch activity",
    )(f)
    return f


def _build_plans_table(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    runs: bool,
    limit: int | None,
    all_users: bool,
    sort: str,
) -> tuple[Table | None, int]:
    """Build plan dashboard table.

    Uses PlanListService to batch all API calls into 2 total:
    1. Single unified GraphQL query for issues + PR linkages
    2. REST API calls for workflow runs (one per issue with run_id)

    Returns:
        Tuple of (table, plan_count). Table is None if no plans found.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Build labels list - default to ["erk-plan"] if no labels specified
    labels_list = list(label) if label else ["erk-plan"]

    # Determine if we need workflow runs (for display or filtering)
    needs_workflow_runs = runs or run_state is not None

    # Get owner/repo from RepoContext (already populated via git remote URL parsing)
    if repo.github is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine repository owner/name")
        raise SystemExit(1)
    owner = repo.github.owner
    repo_name = repo.github.repo

    # Determine creator filter: None for all users, authenticated username otherwise
    creator: str | None = None
    if not all_users:
        is_authenticated, username, _ = ctx.github.check_auth_status()
        if is_authenticated and username:
            creator = username

    # Use PlanListService for batched API calls
    # Skip workflow runs when not needed for better performance
    # PR linkages are always fetched via unified GraphQL query (no performance penalty)
    try:
        location = GitHubRepoLocation(root=repo_root, repo_id=GitHubRepoId(owner, repo_name))
        plan_data = ctx.plan_list_service.get_plan_list_data(
            location=location,
            labels=labels_list,
            state=state,
            limit=limit,
            skip_workflow_runs=not needs_workflow_runs,
            creator=creator,
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Convert IssueInfo to Plan objects
    plans = [_issue_to_plan(issue) for issue in plan_data.issues]

    if not plans:
        return None, 0

    # Use pre-fetched data from PlanListService
    pr_linkages = plan_data.pr_linkages
    workflow_runs = plan_data.workflow_runs

    # Build local worktree mapping from .impl/issue.json files
    worktree_by_issue: dict[int, str] = {}
    worktrees = ctx.git.list_worktrees(repo_root)
    for worktree in worktrees:
        impl_folder = worktree.path / ".impl"
        if impl_folder.exists() and impl_folder.is_dir():
            issue_ref = read_issue_reference(impl_folder)
            if issue_ref is not None:
                # If multiple worktrees have same issue, keep first found
                if issue_ref.issue_number not in worktree_by_issue:
                    worktree_by_issue[issue_ref.issue_number] = worktree.path.name

    # Apply run state filter if specified
    if run_state:
        filtered_plans: list[Plan] = []
        for plan in plans:
            # Get workflow run (keyed by issue number)
            plan_issue_number = plan.metadata.get("number")
            workflow_run = None
            if isinstance(plan_issue_number, int):
                workflow_run = workflow_runs.get(plan_issue_number)
            if workflow_run is None:
                # No workflow run - skip this plan when filtering
                continue
            plan_run_state = get_workflow_run_state(workflow_run)
            if plan_run_state == run_state:
                filtered_plans.append(plan)
        plans = filtered_plans

        # Check if filtering resulted in no plans
        if not plans:
            return None, 0

    # Build activity timestamps for display column (always computed)
    trunk = ctx.git.detect_trunk_branch(repo_root)

    # Build issue -> branch mapping from worktrees
    issue_to_branch: dict[int, str] = {}
    for wt in worktrees:
        impl_folder = wt.path / ".impl"
        if impl_folder.exists() and impl_folder.is_dir():
            issue_ref = read_issue_reference(impl_folder)
            if issue_ref is not None and wt.branch is not None:
                issue_to_branch[issue_ref.issue_number] = wt.branch

    # Build activity timestamps for display and sorting
    activity_by_issue: dict[int, str] = {}
    for issue_num, branch in issue_to_branch.items():
        timestamp = ctx.git.get_branch_last_commit_time(repo_root, branch, trunk)
        if timestamp is not None:
            activity_by_issue[issue_num] = timestamp

    # Apply activity-based sorting if requested
    if sort == "activity":

        def get_last_commit_time(plan: Plan) -> tuple[bool, datetime]:
            """Return sort key: (has_local_activity, commit_time).

            Plans with local activity sort first (by recency), then others by issue#.
            """
            issue_number = plan.metadata.get("number")
            if not isinstance(issue_number, int) or issue_number not in activity_by_issue:
                return (False, datetime.min)
            return (True, datetime.fromisoformat(activity_by_issue[issue_number]))

        # Sort: plans with local activity first (by recency), then others by issue#
        plans = sorted(plans, key=get_last_commit_time, reverse=True)

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create Rich table with columns
    table = Table(show_header=True, header_style="bold")
    table.add_column("plan", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=True)
    table.add_column("pr", no_wrap=True)
    table.add_column("chks", no_wrap=True)
    table.add_column("lcl-wt", no_wrap=True)
    table.add_column("lcl-actvty", no_wrap=True)
    table.add_column("lcl-impl", no_wrap=True)
    if runs:
        table.add_column("remote-impl", no_wrap=True)
        table.add_column("run-id", no_wrap=True)
        table.add_column("run-state", no_wrap=True, width=12)

    # Populate table rows
    for plan in plans:
        # Format issue number with clickable OSC 8 hyperlink
        id_text = f"#{plan.plan_identifier}"
        colored_id = f"[cyan]{id_text}[/cyan]"

        # Make ID clickable using OSC 8 if URL is available
        if plan.url:
            # Rich library supports OSC 8 via markup syntax
            issue_id = f"[link={plan.url}]{colored_id}[/link]"
        else:
            issue_id = colored_id

        # Truncate title to 50 characters with ellipsis
        title = plan.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Query worktree status - check local .impl/issue.json first, then issue body
        issue_number = plan.metadata.get("number")
        worktree_name = ""
        exists_locally = False
        last_local_impl_at: str | None = None
        last_local_impl_event: str | None = None
        last_remote_impl_at: str | None = None

        # Check local mapping first (worktree exists locally)
        if isinstance(issue_number, int) and issue_number in worktree_by_issue:
            worktree_name = worktree_by_issue[issue_number]
            exists_locally = True

        # Extract from issue body - worktree may or may not exist locally
        if plan.body:
            extracted = extract_plan_header_worktree_name(plan.body)
            if extracted:
                # If we don't have a local name yet, use the one from issue body
                if not worktree_name:
                    worktree_name = extracted
            # Extract implementation timestamps and event
            last_local_impl_at = extract_plan_header_local_impl_at(plan.body)
            last_local_impl_event = extract_plan_header_local_impl_event(plan.body)
            last_remote_impl_at = extract_plan_header_remote_impl_at(plan.body)

        # Format the worktree cells
        worktree_name_cell = format_worktree_name_cell(worktree_name, exists_locally)
        local_run_cell = format_local_run_cell(last_local_impl_at, last_local_impl_event)
        remote_run_cell = format_remote_run_cell(last_remote_impl_at)

        # Get PR info for this issue
        pr_cell = "-"
        checks_cell = "-"
        if isinstance(issue_number, int) and issue_number in pr_linkages:
            issue_prs = pr_linkages[issue_number]
            selected_pr = select_display_pr(issue_prs)
            if selected_pr is not None:
                graphite_url = ctx.graphite.get_graphite_url(
                    GitHubRepoId(selected_pr.owner, selected_pr.repo), selected_pr.number
                )
                pr_cell = format_pr_cell(
                    selected_pr, use_graphite=use_graphite, graphite_url=graphite_url
                )
                checks_cell = format_checks_cell(selected_pr)

        # Get workflow run for this plan (keyed by issue number)
        run_id_cell = "-"
        workflow_run = None
        if isinstance(issue_number, int):
            workflow_run = workflow_runs.get(issue_number)
        if workflow_run is not None:
            # Build workflow URL from plan.url attribute
            workflow_url = None
            if plan.url:
                # Parse owner/repo from URL like https://github.com/owner/repo/issues/123
                parts = plan.url.split("/")
                if len(parts) >= 5:
                    owner = parts[-4]
                    repo_name = parts[-3]
                    workflow_url = (
                        f"https://github.com/{owner}/{repo_name}/actions/runs/{workflow_run.run_id}"
                    )
            # Format the run ID with linkification
            run_id_cell = format_workflow_run_id(workflow_run, workflow_url)

        # Format workflow run outcome
        run_outcome_cell = format_workflow_outcome(workflow_run)

        # Format activity cell (last commit time on local branch)
        activity_cell = "-"
        if isinstance(issue_number, int) and issue_number in activity_by_issue:
            activity_cell = format_relative_time(activity_by_issue[issue_number]) or "-"

        # Build row based on which columns are enabled
        row: list[str] = [
            issue_id,
            title,
            pr_cell,
            checks_cell,
            worktree_name_cell,
            activity_cell,
            local_run_cell,
        ]
        if runs:
            row.extend([remote_run_cell, run_id_cell, run_outcome_cell])
        table.add_row(*row)

    return table, len(plans)


def _list_plans_impl(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    runs: bool,
    limit: int | None,
    all_users: bool,
    sort: str,
) -> None:
    """Implementation logic for listing plans with optional filters."""
    table, plan_count = _build_plans_table(
        ctx, label, state, run_state, runs, limit, all_users, sort
    )

    if table is None:
        user_output("No plans found matching the criteria.")
        return

    # Display results header
    user_output(f"\nFound {plan_count} plan(s):\n")

    # Output table to stderr (consistent with user_output convention)
    # Use width=200 to ensure proper display without truncation
    # force_terminal=True ensures hyperlinks render even when Rich doesn't detect a TTY
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()  # Add blank line after table


def _build_watch_content(
    table: Table | None,
    count: int,
    last_update: str,
    seconds_remaining: int,
    fetch_duration_secs: float | None = None,
) -> Group | Panel:
    """Build display content for watch mode.

    Args:
        table: The plans table, or None if no plans
        count: Number of plans found
        last_update: Formatted time of last data refresh
        seconds_remaining: Seconds until next refresh
        fetch_duration_secs: Duration of last data fetch in seconds, or None

    Returns:
        Rich renderable content for the display
    """
    # Build duration suffix
    duration_suffix = f" ({fetch_duration_secs:.1f}s)" if fetch_duration_secs is not None else ""

    footer = (
        f"Found {count} plan(s) | Updated: {last_update}{duration_suffix} | "
        f"Next refresh: {seconds_remaining}s | Ctrl+C to exit"
    )

    if table is None:
        return Panel(f"No plans found.\n\n{footer}", title="erk dash --watch")
    else:
        return Group(table, Panel(footer, style="dim"))


def _run_watch_loop(
    ctx: ErkContext,
    live_display: LiveDisplay,
    build_table_fn: Callable[[], tuple[Table | None, int]],
    interval: float,
) -> None:
    """Run watch loop until KeyboardInterrupt.

    Updates display every second with countdown timer. Fetches fresh data
    when countdown reaches zero.

    Args:
        ctx: ErkContext with time abstraction
        live_display: Display renderer for live updates
        build_table_fn: Function that returns (table, count)
        interval: Seconds between data refreshes
    """
    live_display.start()
    try:
        # Initial data fetch - with timing
        start = ctx.time.now()
        table, count = build_table_fn()
        fetch_duration_secs = (ctx.time.now() - start).total_seconds()
        last_update = ctx.time.now().strftime("%H:%M:%S")
        seconds_remaining = int(interval)

        while True:
            # Update display with current countdown
            content = _build_watch_content(
                table, count, last_update, seconds_remaining, fetch_duration_secs
            )
            live_display.update(content)

            # Sleep for 1 second
            ctx.time.sleep(1.0)
            seconds_remaining -= 1

            # Refresh data when countdown reaches zero
            if seconds_remaining <= 0:
                start = ctx.time.now()
                table, count = build_table_fn()
                fetch_duration_secs = (ctx.time.now() - start).total_seconds()
                last_update = ctx.time.now().strftime("%H:%M:%S")
                seconds_remaining = int(interval)
    except KeyboardInterrupt:
        pass
    finally:
        live_display.stop()


def _run_interactive_mode(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    runs: bool,
    prs: bool,
    limit: int | None,
    interval: float,
    all_users: bool,
    sort: str,
) -> None:
    """Run interactive TUI mode.

    Args:
        ctx: ErkContext with all dependencies
        label: Labels to filter by
        state: State filter ("open", "closed", or None)
        run_state: Workflow run state filter
        runs: Whether to show run columns
        prs: Whether to show PR columns
        limit: Maximum number of results
        interval: Refresh interval in seconds
        all_users: If True, show plans from all users; if False, filter to authenticated user
        sort: Sort order ("issue" or "activity")
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Get owner/repo from RepoContext (already populated via git remote URL parsing)
    if repo.github is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine repository owner/name")
        raise SystemExit(1)
    owner = repo.github.owner
    repo_name = repo.github.repo

    # Determine creator filter: None for all users, authenticated username otherwise
    creator: str | None = None
    if not all_users:
        is_authenticated, username, _ = ctx.github.check_auth_status()
        if is_authenticated and username:
            creator = username

    # Build labels - default to ["erk-plan"]
    labels = label if label else ("erk-plan",)

    # Create data provider and filters
    location = GitHubRepoLocation(root=repo_root, repo_id=GitHubRepoId(owner, repo_name))
    clipboard = RealClipboard()
    browser = RealBrowserLauncher()
    provider = RealPlanDataProvider(ctx, location, clipboard, browser)
    filters = PlanFilters(
        labels=labels,
        state=state,
        run_state=run_state,
        limit=limit,
        show_prs=prs,
        show_runs=runs,
        creator=creator,
    )

    # Convert sort string to SortState
    initial_sort = SortState(
        key=SortKey.BRANCH_ACTIVITY if sort == "activity" else SortKey.ISSUE_NUMBER
    )

    # Run the TUI app
    app = ErkDashApp(provider, filters, refresh_interval=interval, initial_sort=initial_sort)
    app.run()


@click.command("list")
@plan_filter_options
@click.option(
    "--runs",
    "-r",
    is_flag=True,
    default=False,
    help="Show workflow run columns (run-id, run-state)",
)
@click.pass_obj
def list_plans(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    limit: int | None,
    all_users: bool,
    sort: str,
    runs: bool,
) -> None:
    """List plans as a static table.

    By default, shows only plans created by you. Use --all-users (-A)
    to show plans from all users.

    Examples:
        erk plan list                    # Your plans only
        erk plan list --all-users        # All users' plans
        erk plan list -A                 # All users' plans (short form)
        erk plan list --state open
        erk plan list --label erk-plan --label bug
        erk plan list --limit 10
        erk plan list --run-state in_progress
        erk plan list --runs
        erk plan list --sort activity    # Sort by recent branch activity
    """
    _list_plans_impl(ctx, label, state, run_state, runs, limit, all_users, sort)


@click.command("dash")
@plan_filter_options
@dash_options
@click.pass_obj
def dash(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    limit: int | None,
    all_users: bool,
    sort: str,  # noqa: ARG001  # Accepted from shared options but not used by TUI
    interval: float,
) -> None:
    """Interactive plan dashboard (TUI).

    By default, shows only plans created by you. Use --all-users (-A)
    to show plans from all users.

    Launches an interactive terminal UI for viewing and managing plans.
    Shows all columns (runs) by default. For a static table output, use
    'erk plan list' instead.

    Examples:
        erk dash                         # Your plans only
        erk dash --all-users             # All users' plans
        erk dash -A                      # All users' plans (short form)
        erk dash --interval 10
        erk dash --label erk-plan --state open
        erk dash --limit 10
        erk dash --run-state in_progress
        erk dash --sort activity         # Sort by recent branch activity
    """
    # Default to showing all columns (runs=True)
    prs = True  # Always show PRs
    runs = True  # Default to showing runs

    _run_interactive_mode(ctx, label, state, run_state, runs, prs, limit, interval, all_users, sort)
