"""List open pull requests authored by the current user."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import get_pr_status_emoji
from erk.core.repo_discovery import NoRepoSentinel, RepoContext


def _format_pr_cell(title: str | None, url: str) -> str:
    """Format PR title cell for Rich table with clickable link.

    Args:
        title: PR title, or None if not available
        url: PR URL for clickable link

    Returns:
        Formatted string for table cell with Rich link markup
    """
    display_title = title if title else "(no title)"
    return f"[link={url}]{display_title}[/link]"


def _format_pr_number_cell(pr_number: int, url: str, emoji: str) -> str:
    """Format PR number cell for Rich table with emoji and clickable link.

    Args:
        pr_number: PR number
        url: PR URL for clickable link
        emoji: Status emoji

    Returns:
        Formatted string for table cell with Rich link markup
    """
    return f"{emoji} [link={url}]#{pr_number}[/link]"


@alias("ls")
@click.command("list")
@click.pass_obj
def pr_list(ctx: ErkContext) -> None:
    """List your open pull requests in the current repository.

    Shows a table with PR number, title, and branch name for all open PRs
    authored by the current GitHub user (@me).

    Examples:

        # List all your open PRs
        erk pr list
        erk pr ls
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.feedback.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Fetch open PRs for current user
    prs = ctx.github.list_my_open_prs(repo.root)

    if not prs:
        ctx.feedback.info("No open pull requests found.")
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("pr", no_wrap=True)
    table.add_column("title", no_wrap=False)

    # Add rows for each PR
    for pr in prs:
        emoji = get_pr_status_emoji(pr)
        pr_cell = _format_pr_number_cell(pr.number, pr.url, emoji)
        title_cell = _format_pr_cell(pr.title, pr.url)
        table.add_row(pr_cell, title_cell)

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)
