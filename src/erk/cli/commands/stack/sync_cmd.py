"""Sync all stack branches with their remote tracking branches."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.graphite_command import GraphiteCommand
from erk.core.context import ErkContext
from erk.core.stack_sync import BranchSyncAction, StackSyncResult, sync_stack


@click.command("sync", cls=GraphiteCommand)
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
    if action == BranchSyncAction.ALREADY_SYNCED:
        return "already in sync"
    if action == BranchSyncAction.FAST_FORWARDED:
        return f"fast-forwarded ({detail})"
    if action == BranchSyncAction.REBASED:
        return f"rebased ({detail})"
    if action == BranchSyncAction.SKIPPED_NO_REMOTE:
        return "skipped (no remote)"
    if action == BranchSyncAction.SKIPPED_OTHER_WORKTREE:
        return f"skipped ({detail})"
    if action == BranchSyncAction.CONFLICT:
        return click.style("CONFLICT", fg="red") + " — run: erk pr diverge-fix"
    if action == BranchSyncAction.ERROR:
        return click.style(f"error: {detail}", fg="red")
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
    fixed = sum(
        1
        for r in result.branch_results
        if r.action in (BranchSyncAction.FAST_FORWARDED, BranchSyncAction.REBASED)
    )
    in_sync = sum(1 for r in result.branch_results if r.action == BranchSyncAction.ALREADY_SYNCED)
    conflicts = sum(1 for r in result.branch_results if r.action == BranchSyncAction.CONFLICT)
    skipped = sum(
        1
        for r in result.branch_results
        if r.action in (BranchSyncAction.SKIPPED_NO_REMOTE, BranchSyncAction.SKIPPED_OTHER_WORKTREE)
    )

    parts = []
    if fixed:
        parts.append(f"{fixed} fixed")
    if in_sync:
        parts.append(f"{in_sync} in sync")
    if conflicts:
        parts.append(f"{conflicts} conflict{'s' if conflicts > 1 else ''}")
    if skipped:
        parts.append(f"{skipped} skipped")

    click.echo(f"Stack synced: {', '.join(parts)}")
