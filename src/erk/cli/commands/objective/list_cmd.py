"""List open objectives."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation


@alias("ls")
@click.command("list")
@click.pass_obj
def list_objectives(ctx: ErkContext) -> None:
    """List open objectives (GitHub issues with erk-objective label)."""
    repo = discover_repo_context(ctx, ctx.cwd)

    repo_info = Ensure.not_none(ctx.repo_info, "Not in a GitHub repository")
    location = GitHubRepoLocation(
        root=repo.root,
        repo_id=GitHubRepoId(owner=repo_info.owner, repo=repo_info.name),
    )

    # Fetch objectives via dedicated service
    plan_data = ctx.objective_list_service.get_objective_list_data(
        location=location,
        state="open",
        limit=None,
        skip_workflow_runs=True,
        creator=None,
    )

    if not plan_data.plans:
        click.echo("No open objectives found.", err=True)
        return

    # Build Rich table with minimal columns
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=False)
    table.add_column("created", no_wrap=True)
    table.add_column("url", no_wrap=True)

    for plan in plan_data.plans:
        table.add_row(
            f"[link={plan.url}]#{plan.plan_identifier}[/link]",
            plan.title,
            format_relative_time(plan.created_at.isoformat()),
            plan.url,
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)
