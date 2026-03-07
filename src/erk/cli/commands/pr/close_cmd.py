"""Command to close a plan."""

from pathlib import Path

import click

from erk.cli.commands.objective_helpers import run_objective_update_after_close
from erk.cli.commands.pr.repo_resolution import (
    get_remote_github,
    is_remote_mode,
    repo_option,
    resolve_owner_repo,
)
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound


def _close_linked_prs(
    ctx: ErkContext,
    repo_root: Path,
    plan_number: int,
) -> list[int]:
    """Close all OPEN PRs linked to a plan (local path).

    Returns list of PR numbers that were closed.
    """
    linked_prs = ctx.issues.get_prs_referencing_issue(repo_root, plan_number)

    closed_prs: list[int] = []
    for pr in linked_prs:
        # Close all OPEN PRs (both drafts and non-drafts per user requirement)
        if pr.state == "OPEN":
            ctx.github.close_pr(repo_root, pr.number)
            closed_prs.append(pr.number)

    return closed_prs


def _close_linked_prs_remote(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    plan_number: int,
) -> list[int]:
    """Close all OPEN PRs linked to a plan (remote path).

    Returns list of PR numbers that were closed.
    """
    linked_prs = remote.get_prs_referencing_issue(owner=owner, repo=repo, number=plan_number)

    closed_prs: list[int] = []
    for pr in linked_prs:
        if pr.state == "OPEN":
            remote.close_pr(owner=owner, repo=repo, number=pr.number)
            closed_prs.append(pr.number)

    return closed_prs


@click.command("close")
@click.argument("identifier", type=str)
@repo_option
@click.pass_obj
def pr_close(ctx: ErkContext, identifier: str, *, target_repo: str | None) -> None:
    """Close a plan by plan number or GitHub URL.

    Closes all OPEN PRs linked to the plan in addition to closing the plan itself.

    Examples:
        erk pr close 42
        erk pr close 42 --repo owner/repo
    """
    if is_remote_mode(ctx, target_repo=target_repo):
        _pr_close_remote(ctx, identifier, target_repo=target_repo)
    else:
        _pr_close_local(ctx, identifier)


def _pr_close_remote(
    ctx: ErkContext,
    identifier: str,
    *,
    target_repo: str | None,
) -> None:
    """Remote path for pr close using RemoteGitHub."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    number = parse_issue_identifier(identifier)

    # Verify plan exists
    issue = remote.get_issue(owner=owner, repo=repo_name, number=number)
    if isinstance(issue, IssueNotFound):
        raise click.ClickException(f"Plan #{number} not found")

    # Close linked PRs before closing the plan
    closed_prs = _close_linked_prs_remote(remote, owner=owner, repo=repo_name, plan_number=number)

    # Close the plan (issue)
    remote.close_issue(owner=owner, repo=repo_name, number=number)

    # Output
    user_output(f"Closed plan #{number}")
    if closed_prs:
        pr_list_str = ", ".join(f"#{pr}" for pr in closed_prs)
        user_output(f"Closed {len(closed_prs)} linked PR(s): {pr_list_str}")


def _pr_close_local(ctx: ErkContext, identifier: str) -> None:
    """Local path for pr close using local git context."""
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse plan number - errors if invalid
    number = parse_issue_identifier(identifier)

    # Fetch plan - errors if not found
    result = ctx.plan_store.get_plan(repo_root, str(number))
    if isinstance(result, PlanNotFound):
        raise click.ClickException(f"Plan #{number} not found")

    # Close linked PRs before closing the plan
    closed_prs = _close_linked_prs(ctx, repo_root, number)

    # Close the plan (issue)
    ctx.plan_store.close_plan(repo_root, identifier)

    # Update objective roadmap if plan is linked to an objective
    if result.objective_id is not None:
        run_objective_update_after_close(
            ctx,
            plan_number=number,
            objective=result.objective_id,
        )

    # Output
    user_output(f"Closed plan #{number}")
    if closed_prs:
        pr_list_str = ", ".join(f"#{pr}" for pr in closed_prs)
        user_output(f"Closed {len(closed_prs)} linked PR(s): {pr_list_str}")
