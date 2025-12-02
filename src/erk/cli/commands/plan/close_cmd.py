"""Command to close a plan."""

from pathlib import Path
from urllib.parse import urlparse

import click
from erk_shared.github.parsing import github_repo_location_from_url
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


def _parse_issue_number(identifier: str) -> int | None:
    """Parse issue number from identifier string.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub issue URL)

    Returns:
        Issue number as int, or None if parsing fails
    """
    if identifier.isdigit():
        return int(identifier)

    # Try to parse from GitHub URL
    parsed = urlparse(identifier)
    if parsed.hostname == "github.com" and parsed.path:
        parts = parsed.path.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2] == "issues":
            last_part = parts[-1]
            if last_part.isdigit():
                return int(last_part)

    return None


def _close_linked_prs(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
    issue_url: str,
) -> list[int]:
    """Close all OPEN PRs linked to an issue.

    Returns list of PR numbers that were closed.
    """
    location = github_repo_location_from_url(repo_root, issue_url)
    if location is None:
        return []
    pr_linkages = ctx.github.get_prs_linked_to_issues(location, [issue_number])
    linked_prs = pr_linkages.get(issue_number, [])

    closed_prs: list[int] = []
    for pr in linked_prs:
        # Close all OPEN PRs (both drafts and non-drafts per user requirement)
        if pr.state == "OPEN":
            ctx.github.close_pr(repo_root, pr.number)
            closed_prs.append(pr.number)

    return closed_prs


@click.command("close")
@click.argument("identifier", type=str)
@click.pass_obj
def close_plan(ctx: ErkContext, identifier: str) -> None:
    """Close a plan by issue number or GitHub URL.

    Closes all OPEN PRs linked to the issue in addition to closing the issue itself.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Parse issue number for PR lookup (before closing the plan)
    number = _parse_issue_number(identifier)

    # Fetch plan to get URL for PR lookup
    plan = None
    if number is not None:
        try:
            plan = ctx.plan_store.get_plan(repo_root, str(number))
        except RuntimeError:
            # Plan not found - will be reported by close_plan below
            pass

    # Close the plan (issue)
    try:
        ctx.plan_store.close_plan(repo_root, identifier)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Close linked PRs (only if we have plan info)
    closed_prs: list[int] = []
    if number is not None and plan is not None:
        closed_prs = _close_linked_prs(ctx, repo_root, number, plan.url)

    # Output
    display_number = number if number is not None else identifier
    user_output(f"Closed plan #{display_number}")
    if closed_prs:
        pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
        user_output(f"Closed {len(closed_prs)} linked PR(s): {pr_list}")
