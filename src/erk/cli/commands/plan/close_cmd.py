"""Command to close a plan."""

from pathlib import Path

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


def _close_linked_prs(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
) -> list[int]:
    """Close all OPEN PRs linked to an issue.

    Returns list of PR numbers that were closed.
    """
    linked_prs = ctx.issues.get_prs_referencing_issue(repo_root, issue_number)

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

    # Parse issue number - errors if invalid
    number = parse_issue_identifier(identifier)

    # Fetch plan - errors if not found
    try:
        _plan = ctx.plan_store.get_plan(repo_root, str(number))
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e

    # Close linked PRs before closing the plan
    closed_prs = _close_linked_prs(ctx, repo_root, number)

    # Close the plan (issue)
    ctx.plan_store.close_plan(repo_root, identifier)

    # Output
    user_output(f"Closed plan #{number}")
    if closed_prs:
        pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
        user_output(f"Closed {len(closed_prs)} linked PR(s): {pr_list}")
