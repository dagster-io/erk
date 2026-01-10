"""Split command display functions - output formatting and user interaction."""

from pathlib import Path

import click

from erk.cli.commands.stack.split_old.plan import SplitPlan
from erk_shared.gateway.console.abc import Console
from erk_shared.output.output import user_output


def display_stack_preview(
    stack_to_split: list[str],
    trunk_branch: str,
    current_branch: str | None,
    plan: SplitPlan,
) -> None:
    """Display which branches will be split and their status.

    Shows visual indicators for:
    - Trunk branch (stays in root)
    - Current branch (already checked out)
    - Branches with existing worktrees
    - Branches that will get new worktrees
    """
    user_output("\n" + click.style("Stack to split:", bold=True))
    for b in stack_to_split:
        if b == trunk_branch:
            marker = f" {click.style('←', fg='cyan')} trunk (stays in root)"
            branch_display = click.style(b, fg="cyan")
        elif b == current_branch:
            marker = f" {click.style('←', fg='bright_green')} current (already checked out)"
            branch_display = click.style(b, fg="bright_green", bold=True)
        elif b in plan.existing_worktrees:
            marker = f" {click.style('✓', fg='green')} already has worktree"
            branch_display = click.style(b, fg="green")
        elif b in plan.branches_to_split:
            marker = f" {click.style('→', fg='yellow')} will create worktree"
            branch_display = click.style(b, fg="yellow")
        else:
            marker = ""
            branch_display = click.style(b, fg="white", dim=True)

        user_output(f"  {branch_display}{marker}")


def display_creation_preview(
    plan: SplitPlan,
    dry_run: bool,
) -> None:
    """Display which worktrees will be created.

    Shows paths for each branch that needs a worktree.
    Returns early if no worktrees need to be created.

    Args:
        plan: The split plan containing branches to split
        dry_run: Whether this is a dry run
    """
    if plan.branches_to_split:
        if dry_run:
            user_output(f"\n{click.style('[DRY RUN] Would create:', fg='yellow', bold=True)}")
        else:
            user_output(f"\n{click.style('Will create:', bold=True)}")

        for branch in plan.branches_to_split:
            worktree_path = plan.target_paths[branch]
            path_text = click.style(str(worktree_path), fg="cyan")
            branch_text = click.style(branch, fg="yellow")
            user_output(f"  - {branch_text} at {path_text}")
    else:
        user_output("\n✅ All branches already have worktrees or are excluded")


def confirm_split(console: Console, *, force: bool, dry_run: bool) -> None:
    """Prompt user for confirmation unless --force or --dry-run.

    Args:
        console: Console for user prompts
        force: Whether to skip confirmation
        dry_run: Whether this is a dry run

    Raises:
        SystemExit: If user declines
    """
    if not force and not dry_run:
        user_output("")
        if not console.confirm("Proceed with creating worktrees?", default=False):
            user_output(click.style("⭕ Aborted", fg="yellow"))
            raise SystemExit(1)


def display_results(
    results: list[tuple[str, Path]],
    dry_run: bool,
) -> None:
    """Display results of split operation.

    Shows created worktrees or dry-run simulation results.

    Args:
        results: List of (branch, worktree_path) tuples
        dry_run: Whether this is a dry run
    """
    if results:
        for branch, worktree_path in results:
            path_text = click.style(str(worktree_path), fg="green")
            branch_text = click.style(branch, fg="yellow")
            if dry_run:
                user_output(f"[DRY RUN] Would create worktree for {branch_text} at {path_text}")
            else:
                user_output(f"✅ Created worktree for {branch_text} at {path_text}")

    # Summary message
    if dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow')}")
    else:
        user_output(f"\n✅ Split complete: created {len(results)} worktree(s)")
