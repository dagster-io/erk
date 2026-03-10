"""Sync all stack branches with their remote tracking branches."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.graphite_command import GraphiteCommand
from erk.core.context import ErkContext
from erk.core.stack_sync import BranchSyncAction, StackSyncResult, sync_stack


@click.command("sync", cls=GraphiteCommand, hidden=True)
@click.pass_obj
def sync_stack_cmd(ctx: ErkContext) -> None:
    """Sync all stack branches with their remote tracking branches.

    Fetches remote state and resolves divergences across the entire Graphite
    stack. For each non-trunk branch, checks if the remote has new commits
    and fast-forwards or rebases as needed. After syncing, restacks the
    entire stack.

    If a rebase has conflicts, aborts the rebase and suggests using
    'erk pr diverge-fix' for that specific branch.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    click.echo("Fetching remote state...")
    click.echo("")

    result = sync_stack(ctx, repo_root=repo.root, cwd=ctx.cwd)

    # Handle fatal errors (detached HEAD, not tracked)
    if not result.branch_results and result.restack_error is not None:
        click.echo(f"Error: {result.restack_error}", err=True)
        raise SystemExit(1)

    _print_branch_results(result)
    _print_restack_status(result)
    _print_summary(result)


def _print_branch_results(result: StackSyncResult) -> None:
    """Print per-branch sync status."""
    for br in result.branch_results:
        label = _format_action(br.action, br.detail)
        click.echo(f"  {br.branch:<24}{label}")

    click.echo("")


def _format_action(action: BranchSyncAction, detail: str) -> str:
    """Format a sync action for display."""
    match action:
        case BranchSyncAction.ALREADY_SYNCED:
            return "already in sync"
        case BranchSyncAction.FAST_FORWARDED:
            return f"fast-forwarded ({detail})"
        case BranchSyncAction.REBASED:
            return f"rebased ({detail})"
        case BranchSyncAction.SKIPPED_NO_REMOTE:
            return "skipped (no remote)"
        case BranchSyncAction.SKIPPED_OTHER_WORKTREE:
            return f"skipped ({detail})"
        case BranchSyncAction.CONFLICT:
            return click.style("CONFLICT", fg="red") + " — run: erk pr diverge-fix"
        case BranchSyncAction.ERROR:
            return click.style(f"error: {detail}", fg="red")
        case _:
            return detail


def _print_restack_status(result: StackSyncResult) -> None:
    """Print restack result."""
    if result.restack_success:
        click.echo("Restacking... done")
    elif result.restack_error is not None:
        click.echo(f"Restacking... {click.style('failed', fg='red')}: {result.restack_error}")

    click.echo("")


def _print_summary(result: StackSyncResult) -> None:
    """Print summary line."""
    counts: dict[str, int] = {"fixed": 0, "in_sync": 0, "conflicts": 0, "skipped": 0}
    for r in result.branch_results:
        match r.action:
            case BranchSyncAction.FAST_FORWARDED | BranchSyncAction.REBASED:
                counts["fixed"] += 1
            case BranchSyncAction.ALREADY_SYNCED:
                counts["in_sync"] += 1
            case BranchSyncAction.CONFLICT:
                counts["conflicts"] += 1
            case BranchSyncAction.SKIPPED_NO_REMOTE | BranchSyncAction.SKIPPED_OTHER_WORKTREE:
                counts["skipped"] += 1

    parts = []
    if counts["fixed"]:
        parts.append(f"{counts['fixed']} fixed")
    if counts["in_sync"]:
        parts.append(f"{counts['in_sync']} in sync")
    if counts["conflicts"]:
        parts.append(f"{counts['conflicts']} conflict{'s' if counts['conflicts'] > 1 else ''}")
    if counts["skipped"]:
        parts.append(f"{counts['skipped']} skipped")

    click.echo(f"Stack synced: {', '.join(parts)}")
