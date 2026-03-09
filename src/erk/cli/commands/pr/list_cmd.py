"""Command to list plans with filtering."""

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import ParamSpec, TypeVar

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from erk.cli.core import discover_repo_context
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option
from erk.core.context import ErkContext
from erk.core.display_utils import strip_rich_markup
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.tui.app import ErkDashApp
from erk.tui.data.real_provider import RealPlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import SortKey, SortState
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.browser.real import RealBrowserLauncher
from erk_shared.gateway.clipboard.real import RealClipboard
from erk_shared.gateway.github.emoji import get_pr_status_emoji
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    IssueFilterState,
    PullRequestInfo,
)
from erk_shared.gateway.plan_service.real import RealPlanService
from erk_shared.output.output import user_output

P = ParamSpec("P")
T = TypeVar("T")


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


def pr_filter_options(f: Callable[P, T]) -> Callable[P, T]:
    """Shared filter options for pr list commands."""
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
        "--stage",
        type=click.Choice(
            ["prompted", "planning", "planned", "impl", "merged", "closed"],
            case_sensitive=False,
        ),
        help="Filter by lifecycle stage",
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
        type=click.Choice(["plan", "activity"], case_sensitive=False),
        default="plan",
        help="Sort order: by plan number (default) or recent branch activity",
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
    return f


def _build_static_table(
    rows: list[PlanRowData],
    *,
    show_pr_column: bool,
) -> Table:
    """Build a Rich static table from PlanRowData rows.

    Column order matches the TUI PlanDataTable exactly.

    Args:
        rows: List of PlanRowData to display
        show_pr_column: Whether to show a separate PR column

    Returns:
        Rich Table populated with rows
    """
    table = Table(show_header=True, header_style="bold")

    # Column setup mirrors PlanDataTable._setup_columns()
    table.add_column("pr", style="cyan", no_wrap=True, width=6)
    table.add_column("stage", no_wrap=True, width=8)
    table.add_column("sts", no_wrap=True, width=4)
    table.add_column("created", no_wrap=True, width=7)
    table.add_column("obj", no_wrap=True, width=5)
    table.add_column("loc", no_wrap=True, width=3)
    table.add_column("branch", no_wrap=True, width=42)
    table.add_column("run-id", no_wrap=True, width=10)
    table.add_column("run", no_wrap=True, width=3)
    table.add_column("author", no_wrap=True, width=9)
    if show_pr_column:
        table.add_column("pr", no_wrap=True, width=10)
    table.add_column("chks", no_wrap=True, width=8)
    table.add_column("cmts", no_wrap=True, width=5)

    for row in rows:
        values = _row_to_static_values(row, show_pr_column=show_pr_column)
        table.add_row(*values)

    return table


def _row_to_static_values(
    row: PlanRowData,
    *,
    show_pr_column: bool,
) -> tuple[str | Text, ...]:
    """Convert PlanRowData to static table cell values.

    Mirrors PlanDataTable._row_to_values() for Rich Console rendering.

    Args:
        row: Plan row data
        show_pr_column: Whether to show a separate PR column

    Returns:
        Tuple of cell values matching column order
    """
    # Format plan/PR number
    plan_cell: str | Text = f"#{row.plan_id}"
    if row.plan_url:
        plan_cell = f"[link={row.plan_url}]#{row.plan_id}[/link]"

    # Format objective cell
    objective_cell: str | Text = row.objective_display
    if row.objective_issue is not None and row.objective_url is not None:
        objective_cell = f"[link={row.objective_url}]{row.objective_display}[/link]"
    elif row.objective_issue is not None:
        objective_cell = Text(row.objective_display, style="cyan")

    # Compact location emoji
    location_parts: list[str] = []
    if row.exists_locally:
        location_parts.append("\U0001f4bb")
    if row.run_url is not None:
        location_parts.append("\u2601")
    location_cell = "".join(location_parts) if location_parts else "-"

    # run-id and run-state
    run_id: str | Text = strip_rich_markup(row.run_id_display)
    if row.run_url:
        run_id = f"[link={row.run_url}]{run_id}[/link]"
    run_state_text = strip_rich_markup(row.run_state_display)
    run_state_emoji = run_state_text.split(" ", 1)[0] if run_state_text.strip() else "-"

    # Build values list matching column order
    stage_display = strip_rich_markup(row.lifecycle_display)
    values: list[str | Text] = [
        plan_cell,
        stage_display,
        row.status_display,
        row.created_display,
        objective_cell,
        location_cell,
        row.pr_head_branch or row.worktree_branch or "-",
        run_id,
        run_state_emoji,
    ]
    values.append(row.author)

    checks_display = strip_rich_markup(row.checks_display)
    comments_display = strip_rich_markup(row.comments_display)
    if show_pr_column:
        pr_display = strip_rich_markup(row.pr_display)
        if row.pr_url:
            pr_display = f"[link={row.pr_url}]{pr_display}[/link]"
        values.extend([pr_display, checks_display, comments_display])
    else:
        values.extend([checks_display, comments_display])
    return tuple(values)


def _pr_list_impl(
    ctx: ErkContext,
    *,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    stage: str | None,
    limit: int | None,
    all_users: bool,
    sort: str,
    repo_id: GitHubRepoId,
) -> None:
    http_client = ctx.http_client
    if http_client is None:
        user_output(click.style("Error: ", fg="red") + "GitHub authentication not available")
        raise SystemExit(1)

    # Determine creator filter via RemoteGitHub (works for both local and remote)
    creator: str | None = None
    if not all_users:
        remote = get_remote_github(ctx)
        is_authenticated, username, _ = remote.check_auth_status()
        if is_authenticated and username:
            creator = username

    labels = label if label else ("erk-pr",)

    # Determine location root
    if not isinstance(ctx.repo, NoRepoSentinel):
        root = ctx.repo.root
    else:
        root = Path(tempfile.gettempdir()) / "erk-remote"

    location = GitHubRepoLocation(
        root=root,
        repo_id=repo_id,
    )

    provider = RealPlanDataProvider(
        ctx,
        location=location,
        http_client=http_client,
    )

    effective_state: IssueFilterState = "closed" if state == "closed" else "open"

    filters = PlanFilters(
        labels=labels,
        state=effective_state,
        run_state=run_state,
        limit=limit,
        show_prs=True,
        show_runs=True,
        exclude_labels=(),
        creator=creator,
        show_pr_column=False,
        lifecycle_stage=stage,
    )

    rows, timings = provider.fetch_plans(filters)

    if timings is not None and timings.warnings:
        for warning in timings.warnings:
            user_output(click.style("Warning: ", fg="yellow") + warning)

    if stage is not None:
        rows = [r for r in rows if strip_rich_markup(r.lifecycle_display).startswith(stage)]

    if not rows:
        user_output("No plans found matching the criteria.")
        return

    # Sort: branch activity only available with local repo
    if sort == "activity" and not isinstance(ctx.repo, NoRepoSentinel):
        sort_key = SortKey.BRANCH_ACTIVITY
        activity_by_plan = provider.fetch_branch_activity(rows)
        rows = sort_plans(rows, sort_key, activity_by_plan=activity_by_plan)
    else:
        sort_key = SortKey.PLAN_ID
        rows = sort_plans(rows, sort_key)

    table = _build_static_table(rows, show_pr_column=False)

    user_output(f"\nFound {len(rows)} plan(s):\n")
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()


def _run_interactive_mode(
    ctx: ErkContext,
    *,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    stage: str | None,
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
        stage: Lifecycle stage filter (e.g., "impl", "planned")
        runs: Whether to show run columns
        prs: Whether to show PR columns
        limit: Maximum number of results
        interval: Refresh interval in seconds
        all_users: If True, show plans from all users; if False, filter to authenticated user
        sort: Sort order ("plan" or "activity")
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
    labels = label if label else ("erk-pr",)

    # Create data provider and filters
    location = GitHubRepoLocation(root=repo_root, repo_id=GitHubRepoId(owner, repo_name))
    clipboard = RealClipboard()
    browser = RealBrowserLauncher()

    http_client = ctx.http_client
    if http_client is None:
        user_output(click.style("Error: ", fg="red") + "GitHub authentication not available")
        raise SystemExit(1)

    provider = RealPlanDataProvider(
        ctx,
        location=location,
        http_client=http_client,
    )
    service = RealPlanService(
        ctx,
        location=location,
        clipboard=clipboard,
        browser=browser,
        http_client=http_client,
    )
    effective_state: IssueFilterState = "closed" if state == "closed" else "open"

    filters = PlanFilters(
        labels=labels,
        state=effective_state,
        run_state=run_state,
        limit=limit,
        show_prs=prs,
        show_runs=runs,
        exclude_labels=(),
        creator=creator,
        show_pr_column=False,
        lifecycle_stage=stage,
    )

    # Convert sort string to SortState
    initial_sort = SortState(key=SortKey.BRANCH_ACTIVITY if sort == "activity" else SortKey.PLAN_ID)

    # Determine cmux integration setting
    cmux_integration = (
        ctx.global_config.cmux_integration if ctx.global_config is not None else False
    )

    # Run the TUI app
    app = ErkDashApp(
        provider=provider,
        service=service,
        filters=filters,
        refresh_interval=interval,
        initial_sort=initial_sort,
        cmux_integration=cmux_integration,
    )
    app.run()


@click.command("list")
@pr_filter_options
@resolved_repo_option
@click.pass_obj
def pr_list(
    ctx: ErkContext,
    *,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    stage: str | None,
    limit: int | None,
    all_users: bool,
    sort: str,
    repo_id: GitHubRepoId,
) -> None:
    """List plans as a static table.

    By default, shows only plans created by you. Use --all-users (-A)
    to show plans from all users.

    Examples:
        erk pr list                      # Your plans only
        erk pr list --all-users          # All users' plans
        erk pr list -A                   # All users' plans (short form)
        erk pr list --state open
        erk pr list --label erk-plan --label bug
        erk pr list --limit 10
        erk pr list --run-state in_progress
        erk pr list --stage impl         # Filter by lifecycle stage
        erk pr list --sort activity      # Sort by recent branch activity
        erk pr list --repo owner/repo    # Remote mode (no local git required)
    """
    _pr_list_impl(
        ctx,
        label=label,
        state=state,
        run_state=run_state,
        stage=stage,
        limit=limit,
        all_users=all_users,
        sort=sort,
        repo_id=repo_id,
    )


@click.command("dash")
@pr_filter_options
@dash_options
@click.pass_obj
def dash(
    ctx: ErkContext,
    *,
    label: tuple[str, ...],
    state: str | None,
    run_state: str | None,
    stage: str | None,
    limit: int | None,
    all_users: bool,
    sort: str,
    interval: float,
) -> None:
    """Interactive plan dashboard (TUI).

    By default, shows only plans created by you. Use --all-users (-A)
    to show plans from all users.

    Launches an interactive terminal UI for viewing and managing plans.
    Shows all columns (runs) by default. For a static table output, use
    'erk pr list' instead.

    Examples:
        erk dash                         # Your plans only
        erk dash --all-users             # All users' plans
        erk dash -A                      # All users' plans (short form)
        erk dash --interval 10
        erk dash --label erk-plan --state open
        erk dash --limit 10
        erk dash --run-state in_progress
        erk dash --stage impl            # Filter by lifecycle stage
        erk dash --sort activity         # Sort by recent branch activity
    """
    # Default to showing all columns (runs=True)
    prs = True  # Always show PRs
    runs = True  # Default to showing runs

    _run_interactive_mode(
        ctx,
        label=label,
        state=state,
        run_state=run_state,
        stage=stage,
        runs=runs,
        prs=prs,
        limit=limit,
        interval=interval,
        all_users=all_users,
        sort=sort,
    )
