"""List workflow runs command."""

import click
from erk_shared.github.emoji import format_checks_cell
from erk_shared.github.parsing import github_repo_location_from_url
from erk_shared.output.output import user_output
from rich.console import Console
from rich.table import Table

from erk.cli.commands.plan.list_cmd import format_pr_cell, select_display_pr
from erk.cli.commands.run.shared import extract_issue_number
from erk.cli.constants import DISPATCH_WORKFLOW_NAME
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_submission_time,
    format_workflow_outcome,
    format_workflow_run_id,
)


def _list_runs(ctx: ErkContext, show_all: bool = False) -> None:
    """List workflow runs in a run-centric table view."""
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # 1. Fetch workflow runs from dispatch workflow
    runs = ctx.github.list_workflow_runs(repo.root, DISPATCH_WORKFLOW_NAME)

    # Handle empty state
    if not runs:
        user_output("No workflow runs found")
        return

    # Filter out runs without plans unless --show-legacy flag is set
    if not show_all:
        runs = [run for run in runs if extract_issue_number(run.display_title) is not None]
        if not runs:
            user_output("No runs with plans found. Use --show-legacy to see all runs.")
            return

    # 2. Extract issue numbers from display_title (format: "123:abc456")
    issue_numbers: list[int] = []
    for run in runs:
        issue_num = extract_issue_number(run.display_title)
        if issue_num is not None:
            issue_numbers.append(issue_num)

    # 3. Fetch issues for titles (using issues interface)
    issues = ctx.issues.list_issues(repo.root, labels=["erk-plan"])
    issue_map = {issue.number: issue for issue in issues}

    # Second filtering pass - remove runs where we can't display title
    if not show_all:
        filtered_runs = []
        for run in runs:
            issue_num = extract_issue_number(run.display_title)
            if issue_num is None:
                continue  # Already filtered, but defensive check

            # Filter if issue not found
            if issue_num not in issue_map:
                continue

            # Filter if title is empty
            issue = issue_map[issue_num]
            if not issue.title or not issue.title.strip():
                continue

            filtered_runs.append(run)

        runs = filtered_runs

        # Show message if ALL runs filtered
        if not runs:
            user_output("No runs with plans found. Use --show-legacy to see all runs.")
            return

    # Extract location from first issue URL (needed for API calls and links)
    location = None
    if issues:
        location = github_repo_location_from_url(repo.root, issues[0].url)

    # 4. Batch fetch PRs linked to issues
    pr_linkages: dict[int, list] = {}
    if issue_numbers and location is not None:
        pr_linkages = ctx.github.get_prs_linked_to_issues(location, issue_numbers)

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # 5. Build table
    table = Table(show_header=True, header_style="bold")
    table.add_column("run-id", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True, width=14)
    table.add_column("submitted", no_wrap=True, width=11)
    table.add_column("plan", no_wrap=True)
    table.add_column("title", no_wrap=True)
    table.add_column("pr", no_wrap=True)
    table.add_column("chks", no_wrap=True)

    for run in runs:
        issue_num = extract_issue_number(run.display_title)

        # Format run-id with link
        workflow_url = None
        if location is not None:
            workflow_url = (
                f"https://github.com/{location.owner}/{location.repo}/actions/runs/{run.run_id}"
            )
        run_id_cell = format_workflow_run_id(run, workflow_url)

        # Format status
        status_cell = format_workflow_outcome(run)

        # Format submission time
        submitted_cell = format_submission_time(run.created_at)

        # Handle legacy runs where we can't parse the issue number
        # Show "X" to indicate "can't parse" vs "-" for "no data"
        if issue_num is None:
            # Legacy format - can't extract issue linkage
            plan_cell = "[dim]X[/dim]"
            title_cell = "[dim]X[/dim]"
            pr_cell = "[dim]X[/dim]"
            checks_cell = "[dim]X[/dim]"
        else:
            # New format - have issue number, try to get data
            issue_url = None
            if location is not None:
                issue_url = (
                    f"https://github.com/{location.owner}/{location.repo}/issues/{issue_num}"
                )
            # Make plan number clickable
            if issue_url:
                plan_cell = f"[link={issue_url}][cyan]#{issue_num}[/cyan][/link]"
            else:
                plan_cell = f"[cyan]#{issue_num}[/cyan]"

            # Get title from issue map
            if issue_num in issue_map:
                issue = issue_map[issue_num]

                title = issue.title
                # Truncate to 50 characters
                if len(title) > 50:
                    title = title[:47] + "..."
                title_cell = title
            else:
                title_cell = "[dim]-[/dim]"

            # Format PR column
            pr_cell = "-"
            checks_cell = "-"
            if issue_num in pr_linkages:
                prs = pr_linkages[issue_num]
                selected_pr = select_display_pr(prs)
                if selected_pr is not None:
                    graphite_url = ctx.graphite.get_graphite_url(
                        selected_pr.owner, selected_pr.repo, selected_pr.number
                    )
                    pr_cell = format_pr_cell(
                        selected_pr, use_graphite=use_graphite, graphite_url=graphite_url
                    )
                    checks_cell = format_checks_cell(selected_pr)

        table.add_row(
            run_id_cell,
            status_cell,
            submitted_cell,
            plan_cell,
            title_cell,
            pr_cell,
            checks_cell,
        )

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()  # Add blank line after table


@click.command("list")
@click.option("--show-legacy", is_flag=True, help="Show all runs including legacy runs.")
@click.pass_obj
def list_runs(ctx: ErkContext, show_legacy: bool) -> None:
    """List GitHub Actions workflow runs for plan implementations."""
    _list_runs(ctx, show_legacy)
