"""List workflow runs command."""

from datetime import UTC, datetime

import click
from rich.console import Console
from rich.markup import escape as escape_markup
from rich.table import Table

from erk.cli.commands.pr.list.cli import format_pr_cell
from erk.cli.commands.run.shared import extract_pr_number
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_submission_time,
    format_workflow_outcome,
    format_workflow_run_id,
)
from erk_shared.gateway.github.emoji import format_checks_cell
from erk_shared.gateway.github.parsing import github_repo_location_from_url
from erk_shared.gateway.github.types import GitHubRepoId, PullRequestInfo, WorkflowRun
from erk_shared.output.output import user_output

_MAX_DISPLAY_RUNS = 50
_PER_WORKFLOW_LIMIT = 20
_MAX_TITLE_LENGTH = 50


def _list_runs(ctx: ErkContext) -> None:
    """List workflow runs in a PR-centric table view."""
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # 1. Fetch workflow runs from all registered workflows
    tagged_runs: list[tuple[WorkflowRun, str]] = []
    for command_name, workflow_file in WORKFLOW_COMMAND_MAP.items():
        workflow_runs = ctx.github.list_workflow_runs(repo.root, workflow_file, _PER_WORKFLOW_LIMIT)
        for run in workflow_runs:
            tagged_runs.append((run, command_name))

    # Deduplicate by run_id (a run belongs to exactly one workflow)
    seen: dict[str, tuple[WorkflowRun, str]] = {}
    for pair in tagged_runs:
        if pair[0].run_id not in seen:
            seen[pair[0].run_id] = pair
    tagged_runs = list(seen.values())

    # Sort by created_at descending (newest first), with None timestamps last
    tagged_runs.sort(
        key=lambda pair: pair[0].created_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    # Limit displayed runs
    tagged_runs = tagged_runs[:_MAX_DISPLAY_RUNS]

    # Handle empty state
    if not tagged_runs:
        user_output("No workflow runs found")
        return

    # 2. Extract PR numbers from display_titles
    run_pr_numbers: dict[str, int] = {}  # run_id → pr_number

    for run, _workflow_name in tagged_runs:
        pr_num = extract_pr_number(run.display_title)
        if pr_num is not None:
            run_pr_numbers[run.run_id] = pr_num

    # 3. Fetch issues (needed for GitHubRepoLocation)
    issues = ctx.issues.list_issues(repo_root=repo.root, labels=["erk-pr"])

    # Extract location from first issue URL (needed for API calls and links)
    location = None
    if issues:
        location = github_repo_location_from_url(repo.root, issues[0].url)

    # 4. Fetch PR info for directly-extracted PR numbers
    pr_info_map: dict[int, PullRequestInfo] = {}  # pr_number → PullRequestInfo
    direct_pr_numbers = set(run_pr_numbers.values())
    if direct_pr_numbers:
        all_open_prs = ctx.github.list_prs(repo.root, state="open")
        for pr_info in all_open_prs.values():
            if pr_info.number in direct_pr_numbers:
                pr_info_map[pr_info.number] = pr_info

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # 6. Build table
    table = Table(show_header=True, header_style="bold")
    table.add_column("run-id", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True, width=14)
    table.add_column("submitted", no_wrap=True, width=11)
    table.add_column("workflow", no_wrap=True, width=14)
    table.add_column("pr", no_wrap=True)
    table.add_column("title", no_wrap=True)
    table.add_column("chks", no_wrap=True)

    for run, workflow_name in tagged_runs:
        pr_num = run_pr_numbers.get(run.run_id)

        # Format run-id with link
        workflow_url = None
        if location is not None:
            workflow_url = f"https://github.com/{location.repo_id.owner}/{location.repo_id.repo}/actions/runs/{run.run_id}"
        run_id_cell = format_workflow_run_id(run, workflow_url)

        # Format status
        status_cell = format_workflow_outcome(run)

        # Format submission time
        submitted_cell = format_submission_time(run.created_at)

        # Format PR-related columns
        if pr_num is None:
            pr_cell = "[dim]-[/dim]"
            title_cell = "[dim]-[/dim]"
            checks_cell = "[dim]-[/dim]"
        else:
            pr_info = pr_info_map.get(pr_num)
            if pr_info is not None:
                graphite_url = ctx.graphite.get_graphite_url(
                    GitHubRepoId(pr_info.owner, pr_info.repo), pr_info.number
                )
                pr_cell = format_pr_cell(
                    pr_info, use_graphite=use_graphite, graphite_url=graphite_url
                )
                title = pr_info.title or "-"
                if len(title) > _MAX_TITLE_LENGTH:
                    title = title[: _MAX_TITLE_LENGTH - 3] + "..."
                title_cell = escape_markup(title)
                checks_cell = format_checks_cell(pr_info)
            else:
                # Have PR number but no details — show number with link
                pr_url = None
                if location is not None:
                    pr_url = f"https://github.com/{location.repo_id.owner}/{location.repo_id.repo}/pull/{pr_num}"
                if pr_url:
                    pr_cell = f"[link={pr_url}][cyan]#{pr_num}[/cyan][/link]"
                else:
                    pr_cell = f"[cyan]#{pr_num}[/cyan]"
                title_cell = "[dim]-[/dim]"
                checks_cell = "[dim]-[/dim]"

        workflow_cell = f"[dim]{workflow_name}[/dim]"

        table.add_row(
            run_id_cell,
            status_cell,
            submitted_cell,
            workflow_cell,
            pr_cell,
            title_cell,
            checks_cell,
        )

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()  # Add blank line after table


@click.command("list")
@click.pass_obj
def list_runs(ctx: ErkContext) -> None:
    """List GitHub Actions workflow runs."""
    _list_runs(ctx)
