"""List pull requests with optional filtering."""

from datetime import datetime
from typing import cast

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import get_pr_status_emoji
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRAuthorFilter, PRStatusFilter


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


def _format_created_at(created_at: str | None) -> str:
    """Format ISO 8601 timestamp to human-readable date.

    Args:
        created_at: ISO 8601 timestamp (e.g., "2024-01-15T10:30:00Z")

    Returns:
        Formatted date string (e.g., "Jan 15") or empty string if None
    """
    if created_at is None:
        return ""
    parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return parsed.strftime("%b %d")


@alias("ls")
@click.command("list")
@click.option(
    "--status",
    type=click.Choice(["open", "closed", "merged", "all"]),
    default="open",
    help="Filter by PR status (default: open)",
)
@click.option(
    "--author",
    type=click.Choice(["@me", "any"]),
    default="@me",
    help="Filter by author (default: @me)",
)
@click.pass_obj
def pr_list(ctx: ErkContext, status: str, author: str) -> None:
    """List pull requests in the current repository.

    Shows a table with PR number and title. By default, shows your open PRs.

    Examples:

        # List your open PRs (default)
        erk pr list
        erk pr ls

        # List all open PRs in the repo
        erk pr list --author any

        # List your closed PRs
        erk pr list --status closed

        # List all PRs (any status, any author)
        erk pr list --status all --author any
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.feedback.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Map CLI lowercase values to uppercase PRStatusFilter enum values
    # The gateway uses GraphQL-style uppercase enum values internally
    status_upper = status.upper()
    assert status_upper in ("OPEN", "CLOSED", "MERGED", "ALL"), f"Invalid status: {status}"
    status_filter = cast(PRStatusFilter, status_upper)
    author_filter = cast(PRAuthorFilter, author)

    # Fetch PRs with filters
    prs = ctx.github.list_prs(repo.root, status_filter, author_filter)

    if not prs:
        ctx.feedback.info(f"No {status} pull requests found.")
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("pr", no_wrap=True)
    table.add_column("created", no_wrap=True)
    table.add_column("title", no_wrap=False)

    # Add rows for each PR
    for pr in prs:
        emoji = get_pr_status_emoji(pr)
        pr_cell = _format_pr_number_cell(pr.number, pr.url, emoji)
        created_cell = _format_created_at(pr.created_at)
        title_cell = _format_pr_cell(pr.title, pr.url)
        table.add_row(pr_cell, created_cell, title_cell)

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)
