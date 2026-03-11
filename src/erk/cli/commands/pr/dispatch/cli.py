"""Dispatch plans for remote AI implementation via GitHub Actions."""

import click

from erk.cli.commands.pr.dispatch.operation import (
    LocalPrDispatchRequest,
    PrDispatchRequest,
    PrDispatchResult,
    load_workflow_config,
    run_local_pr_dispatch,
    run_pr_dispatch,
)
from erk.cli.commands.pr.dispatch_helpers import ensure_trunk_synced
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.repo_resolution import repo_option, resolve_owner_repo
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.output.output import user_output


def _print_dispatch_summary(results: list[PrDispatchResult]) -> None:
    """Print summary of all dispatched plans."""
    user_output("")
    count = len(results)
    user_output(click.style("\u2713", fg="green") + f" {count} PR(s) dispatched successfully!")
    user_output("")
    user_output("Dispatched PRs:")
    for r in results:
        user_output(f"  #{r.pr_number}: {r.plan_title}")
        user_output(f"    Plan: {r.plan_url}")
        if r.impl_pr_url:
            user_output(f"    PR: {r.impl_pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")


@click.command("dispatch")
@click.argument("pr_numbers", type=int, nargs=-1, required=False)
@click.option(
    "--base",
    type=str,
    default=None,
    help="Base branch for PR (defaults to current branch).",
)
@click.option(
    "--ref",
    "dispatch_ref",
    type=str,
    default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)",
)
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@repo_option
@click.pass_obj
def pr_dispatch(
    ctx: ErkContext,
    pr_numbers: tuple[int, ...],
    base: str | None,
    dispatch_ref: str | None,
    ref_current: bool,
    *,
    target_repo: str | None,
) -> None:
    """Dispatch plans for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then dispatches the plan-implement.yml GitHub Actions workflow.

    With --repo, operates entirely via the GitHub REST API without
    requiring a local git clone.

    Arguments:
        PLAN_NUMBERS: One or more plan numbers to dispatch.
            If omitted, auto-detects from the resolved implementation directory or current branch.

    \b
    Example:
        erk pr dispatch 123
        erk pr dispatch 123 456 789
        erk pr dispatch 123 --base master
        erk pr dispatch                     # auto-detect from context
        erk pr dispatch 123 --repo owner/repo  # remote mode

    Requires:
        - All issues must have [erk-pr] title prefix
        - All issues must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Remote mode: --repo flag or no local git repo
    is_remote = target_repo is not None or isinstance(ctx.repo, NoRepoSentinel)

    if is_remote:
        owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)

        if not pr_numbers:
            user_output(
                click.style("Error: ", fg="red") + "PR number(s) required in remote mode.\n\n"
                "Usage: erk pr dispatch <number> --repo owner/repo"
            )
            raise SystemExit(1)

        results: list[PrDispatchResult] = []
        for i, pr_number in enumerate(pr_numbers):
            if len(pr_numbers) > 1:
                user_output(f"--- Dispatching PR {i + 1}/{len(pr_numbers)}: #{pr_number} ---")
            else:
                user_output(f"Dispatching PR #{pr_number}...")
            user_output("")

            request = PrDispatchRequest(pr_number=pr_number, base_branch=base, ref=dispatch_ref)
            result = run_pr_dispatch(ctx, request, owner=owner, repo_name=repo_name)
            if isinstance(result, MachineCommandError):
                user_output(click.style("Error: ", fg="red") + result.message)
                raise SystemExit(1)
            results.append(result)
            user_output("")

        _print_dispatch_summary(results)
    else:
        # Local mode: validate GitHub CLI prerequisites upfront (LBYL)
        user_output("Checking GitHub authentication...")
        Ensure.gh_authenticated(ctx)

        # Get repository context
        if isinstance(ctx.repo, RepoContext):
            repo = ctx.repo
        else:
            repo = discover_repo_context(ctx, ctx.cwd)

        # Ensure trunk is synced before any operations
        user_output("Syncing trunk with remote...")
        ensure_trunk_synced(ctx, repo)

        ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
        request_local = LocalPrDispatchRequest(
            pr_numbers=pr_numbers,
            base_branch=base,
            ref=ref,
        )
        local_result = run_local_pr_dispatch(ctx, repo, request_local)
        if isinstance(local_result, MachineCommandError):
            user_output(click.style("Error: ", fg="red") + local_result.message)
            raise SystemExit(1)

        _print_dispatch_summary(local_result)


# Re-export load_workflow_config for backwards compatibility
__all__ = ["load_workflow_config", "pr_dispatch"]
