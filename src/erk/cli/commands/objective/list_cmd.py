"""List open objectives."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time


@alias("ls")
@click.command("list")
@click.pass_obj
def list_objectives(ctx: ErkContext) -> None:
    """List open objectives (GitHub issues with erk-objective label)."""
    repo = discover_repo_context(ctx, ctx.cwd)

    # Fetch objectives via issues interface
    issues = ctx.issues.list_issues(
        repo_root=repo.root,
        labels=["erk-objective"],
        state="open",
    )

    if not issues:
        click.echo("No open objectives found.", err=True)
        return

    # Build Rich table with minimal columns
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=False)
    table.add_column("created", no_wrap=True)
    table.add_column("url", no_wrap=True)

    for issue in issues:
        table.add_row(
            f"[link={issue.url}]#{issue.number}[/link]",
            issue.title,
            format_relative_time(issue.created_at.isoformat()),
            issue.url,
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)
