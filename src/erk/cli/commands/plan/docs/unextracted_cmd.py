"""Command to list closed plans that haven't been analyzed for documentation."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.constants import DOCS_EXTRACTED_LABEL, ERK_PLAN_LABEL
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


@click.command("unextracted")
@click.pass_obj
def list_unextracted(ctx: ErkContext) -> None:
    """List closed plans that haven't been analyzed for documentation.

    Shows all closed erk-plan issues that don't have the docs-extracted label.
    Use 'erk plan docs extract <number>' to mark a plan as extracted.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Query all closed issues with erk-plan label
    try:
        issues = ctx.issues.list_issues(
            repo_root,
            labels=[ERK_PLAN_LABEL],
            state="closed",
        )
    except RuntimeError as e:
        raise click.ClickException(f"Failed to list issues: {e}") from e

    # Filter out issues that already have docs-extracted label
    unextracted = [issue for issue in issues if DOCS_EXTRACTED_LABEL not in issue.labels]

    if not unextracted:
        user_output("No unextracted plans found. All closed plans have been analyzed.")
        return

    # Build table
    table = Table(show_header=True, header_style="bold")
    table.add_column("plan", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=True)
    table.add_column("closed", no_wrap=True)

    for issue in unextracted:
        # Format issue number with link
        id_text = f"#{issue.number}"
        if issue.url:
            issue_id = f"[link={issue.url}][cyan]{id_text}[/cyan][/link]"
        else:
            issue_id = f"[cyan]{id_text}[/cyan]"

        # Truncate title
        title = issue.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Format closed time
        closed_at = format_relative_time(issue.updated_at.isoformat()) if issue.updated_at else "-"

        table.add_row(issue_id, title, closed_at)

    user_output(f"\nFound {len(unextracted)} unextracted plan(s):\n")

    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()
