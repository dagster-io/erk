"""Command to list plans with filtering."""

from collections.abc import Callable

import click
from erk_shared.github.emoji import format_checks_cell, get_pr_status_emoji
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata import (
    extract_plan_header_local_impl_at,
    extract_plan_header_remote_impl_at,
    extract_plan_header_worktree_name,
)
from erk_shared.github.types import PullRequestInfo
from erk_shared.impl_folder import read_issue_reference
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan, PlanState
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display import LiveDisplay, RealLiveDisplay
from erk.core.display_utils import (
    format_relative_time,
    format_workflow_outcome,
    format_workflow_run_id,
    get_workflow_run_state,
)
from erk.core.repo_discovery import ensure_erk_metadata_dir


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


def select_display_pr(prs: list[PullRequestInfo]) -> PullRequestInfo | None:
    """Select PR to display: prefer open, then merged, then closed.

    Args:
        prs: List of PRs sorted by created_at descending (most recent first)

    Returns:
        PR to display, or None if no PRs
    """
    # Check for open PRs (published or draft)
    open_prs = [pr for pr in prs if pr.state in ("OPEN", "DRAFT")]
    if open_prs:
        return open_prs[0]  # Most recent open

    # Fallback to merged PRs
    merged_prs = [pr for pr in prs if pr.state == "MERGED"]
    if merged_prs:
        return merged_prs[0]  # Most recent merged

    # Fallback to closed PRs
    closed_prs = [pr for pr in prs if pr.state == "CLOSED"]
    if closed_prs:
        return closed_prs[0]  # Most recent closed

    return None


def format_pr_cell(pr: PullRequestInfo, *, use_graphite: bool, graphite_url: str | None) -> str:
    """Format PR cell with clickable link and emoji: #123 👀 or #123 👀💥

    Args:
        pr: PR information
        use_graphite: If True, use Graphite URL; if False, use GitHub URL
        graphite_url: Graphite URL for the PR (None if unavailable)

    Returns:
        Formatted string for table cell with OSC 8 hyperlink
    """
    emoji = get_pr_status_emoji(pr)
    pr_text = f"#{pr.number}"

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


def format_local_run_cell(last_local_impl_at: str | None) -> str:
    """Format last local implementation timestamp as relative time.

    Args:
        last_local_impl_at: ISO timestamp of last local implementation, or None

    Returns:
        Relative time string (e.g., "2h ago") or "-" if no timestamp
    """
    relative_time = format_relative_time(last_local_impl_at)
    return relative_time if relative_time else "-"


def format_remote_run_cell(last_remote_impl_at: str | None) -> str:
    """Format last remote implementation timestamp as relative time.

    Args:
        last_remote_impl_at: ISO timestamp of last remote (GitHub Actions) implementation, or None

    Returns:
        Relative time string (e.g., "2h ago") or "-" if no timestamp
    """
    relative_time = format_relative_time(last_remote_impl_at)
    return relative_time if relative_time else "-"


def plan_list_options[**P, T](f: Callable[P, T]) -> Callable[P, T]:
    """Shared options for list/ls commands."""
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
        "--runs",
        "-r",
        is_flag=True,
        default=False,
        help="Show workflow run columns (run-id, run-state)",
    )(f)
    f = click.option(
        "--prs",
        "-P",
        is_flag=True,
        default=False,
        help="Show PR columns (pr, chks) - requires additional API calls",
    )(f)
    f = click.option(
        "--limit",
        type=int,
        help="Maximum number of results to return",
    )(f)
    f = click.option(
        "--all",
        "-a",
        "show_all",  # Use 'show_all' to avoid shadowing Python built-in 'all'
        is_flag=True,
        default=False,
        help="Show all columns (equivalent to -P -r)",
    )(f)
    f = click.option(
        "--watch",
        "-w",
        is_flag=True,
        default=False,
        help="Watch mode: refresh dashboard at regular intervals",
    )(f)
    f = click.option(
        "--interval",
        type=float,
        default=5.0,
        help="Refresh interval in seconds for watch mode (default: 5.0)",
    )(f)
    return f


def _build_plans_table(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    runs: bool,
    prs: bool,
    limit: int | None,
) -> tuple[Table | None, int]:
    """Build plan dashboard table.

    Uses PlanListService to batch all API calls into 3 total:
    1. Single GraphQL query for issues
    2. Single GraphQL query for PRs (only if --prs flag is set)
    3. REST API calls for workflow runs (one per issue with run_id)

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

    # Use PlanListService for batched API calls
    # Skip workflow runs when not needed for better performance
    # Skip PR linkages when --prs flag is not set for better performance
    try:
        plan_data = ctx.plan_list_service.get_plan_list_data(
            repo_root=repo_root,
            labels=labels_list,
            state=state,
            limit=limit,
            skip_workflow_runs=not needs_workflow_runs,
            skip_pr_linkages=not prs,
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

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create Rich table with columns
    table = Table(show_header=True, header_style="bold")
    table.add_column("plan", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=True)
    if prs:
        table.add_column("pr", no_wrap=True)
        table.add_column("chks", no_wrap=True)
    table.add_column("local-wt", no_wrap=True)
    table.add_column("local-run", no_wrap=True)
    if runs:
        table.add_column("remote-run", no_wrap=True)
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
        last_remote_impl_at: str | None = None

        # Check local mapping first (worktree exists locally)
        if isinstance(issue_number, int) and issue_number in worktree_by_issue:
            worktree_name = worktree_by_issue[issue_number]
            exists_locally = True

        # Extract from issue body (schema v2 only) - worktree may or may not exist locally
        if plan.body:
            extracted = extract_plan_header_worktree_name(plan.body)
            if extracted:
                # If we don't have a local name yet, use the one from issue body
                if not worktree_name:
                    worktree_name = extracted
            # Extract implementation timestamps
            last_local_impl_at = extract_plan_header_local_impl_at(plan.body)
            last_remote_impl_at = extract_plan_header_remote_impl_at(plan.body)

        # Format the worktree cells
        worktree_name_cell = format_worktree_name_cell(worktree_name, exists_locally)
        local_run_cell = format_local_run_cell(last_local_impl_at)
        remote_run_cell = format_remote_run_cell(last_remote_impl_at)

        # Get PR info for this issue
        pr_cell = "-"
        checks_cell = "-"
        if isinstance(issue_number, int) and issue_number in pr_linkages:
            issue_prs = pr_linkages[issue_number]
            selected_pr = select_display_pr(issue_prs)
            if selected_pr is not None:
                graphite_url = ctx.graphite.get_graphite_url(
                    selected_pr.owner, selected_pr.repo, selected_pr.number
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

        # Build row based on which columns are enabled
        row: list[str] = [issue_id, title]
        if prs:
            row.extend([pr_cell, checks_cell])
        row.extend([worktree_name_cell, local_run_cell])
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
    prs: bool,
    limit: int | None,
) -> None:
    """Implementation logic for listing plans with optional filters."""
    table, plan_count = _build_plans_table(ctx, label, state, run_state, runs, prs, limit)

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


@click.command("dash")
@plan_list_options
@click.pass_obj
def dash(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    runs: bool,
    prs: bool,
    limit: int | None,
    show_all: bool,
    watch: bool,
    interval: float,
) -> None:
    """Display plan dashboard with optional filters.

    Examples:
        erk dash
        erk dash --watch
        erk dash -w --interval 10
        erk dash -a --watch
        erk dash --label erk-plan --state open
        erk dash --limit 10
        erk dash --run-state in_progress
        erk dash --run-state success --state open
        erk dash --runs
        erk dash --prs
        erk dash --all
        erk dash -a
    """
    # Handle --all flag (equivalent to -P -r)
    if show_all:
        prs = True
        runs = True

    if watch:
        live_display = RealLiveDisplay()

        def build_fn() -> tuple[Table | None, int]:
            return _build_plans_table(ctx, label, state, run_state, runs, prs, limit)

        _run_watch_loop(ctx, live_display, build_fn, interval)
    else:
        _list_plans_impl(ctx, label, state, run_state, runs, prs, limit)
