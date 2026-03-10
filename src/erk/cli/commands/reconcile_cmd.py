"""Reconcile locally-tracked branches that were merged remotely.

Detects branches whose PRs were merged outside `erk land` (e.g., via GitHub
web UI, mobile, or API) and runs the same post-merge lifecycle: learn PR
creation, objective updates, and branch/worktree cleanup.
"""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.commands.reconcile_pipeline import (
    ReconcileBranchInfo,
    ReconcileResult,
    detect_merged_branches,
    process_merged_branch,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("reconcile", hidden=True)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--skip-learn", is_flag=True, help="Skip creating learn plans")
@click.pass_obj
def reconcile(ctx: ErkContext, *, force: bool, dry_run: bool, skip_learn: bool) -> None:
    """Reconcile branches merged outside erk land.

    Detects local branches whose remote tracking refs have been pruned
    (indicating the PR was merged on GitHub) and runs post-merge lifecycle
    operations: learn PR creation, objective updates, and branch cleanup.

    Examples:

    \b
      # Preview what would be reconciled
      erk reconcile --dry-run

    \b
      # Reconcile without prompts
      erk reconcile --force

    \b
      # Skip learn PR creation
      erk reconcile --skip-learn
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    if repo.main_repo_root is None:
        raise click.ClickException("Could not determine main repository root.")
    main_repo_root = repo.main_repo_root

    # Detect merged branches
    click.echo(click.style("Fetching and detecting merged branches...", fg="yellow"))
    candidates = detect_merged_branches(ctx, repo_root=repo.root, main_repo_root=main_repo_root)

    if not candidates:
        click.echo("Nothing to reconcile.")
        return

    # Display candidates table
    _display_candidates(candidates, dry_run=dry_run)

    # Confirm unless --force or --dry-run
    if not force and not dry_run:
        proceed = ctx.console.confirm(
            f"Process {len(candidates)} merged branch(es)?",
            default=True,
        )
        if not proceed:
            click.echo("Aborted.")
            return

    if dry_run:
        click.echo(click.style("Dry run — no changes made.", fg="yellow"))
        return

    # Process each branch
    results: list[ReconcileResult] = []
    for info in candidates:
        user_output("")
        user_output(click.style(f"Processing {info.branch}...", fg="cyan"))
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=main_repo_root,
            repo=repo,
            cwd=ctx.cwd,
            dry_run=dry_run,
            skip_learn=skip_learn,
        )
        results.append(result)

    # Pull trunk
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)
    current_branch = ctx.git.branch.get_current_branch(repo.root)
    if current_branch == trunk:
        click.echo("")
        click.echo(click.style("Pulling trunk...", fg="yellow"))
        try:
            ctx.git.remote.pull_branch(repo.root, "origin", trunk, ff_only=True)
        except RuntimeError:
            user_output(click.style("Warning: ", fg="yellow") + "Failed to pull trunk")

    # Display summary
    _display_results(results)


def _display_candidates(candidates: list[ReconcileBranchInfo], *, dry_run: bool) -> None:
    """Display table of branches to reconcile."""
    label = "Branches to reconcile (dry run):" if dry_run else "Branches to reconcile:"
    click.echo("")
    click.echo(click.style(label, bold=True))

    table = Table(show_edge=False, box=None, padding=(0, 2), pad_edge=False)
    table.add_column("Branch", no_wrap=True)
    table.add_column("PR", no_wrap=True)
    table.add_column("Title", no_wrap=True)
    table.add_column("Plan", no_wrap=True)
    table.add_column("Objective", no_wrap=True)
    table.add_column("Worktree", no_wrap=True)

    for info in candidates:
        table.add_row(
            info.branch,
            f"#{info.pr_number}",
            info.pr_title or "",
            f"#{info.plan_id}" if info.plan_id else "-",
            f"#{info.objective_number}" if info.objective_number else "-",
            str(info.worktree_path) if info.worktree_path else "-",
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)
    click.echo("")


def _display_results(results: list[ReconcileResult]) -> None:
    """Display summary table of reconciliation results."""
    click.echo("")
    click.echo(click.style("Reconciliation complete:", bold=True))

    successes = sum(1 for r in results if r.error is None)
    failures = len(results) - successes

    for result in results:
        if result.error is None:
            status = click.style("ok", fg="green")
        else:
            status = click.style("FAIL", fg="red")
        parts = [f"  {status}  {result.branch}"]
        actions: list[str] = []
        if result.learn_created:
            actions.append("learn")
        if result.objective_updated:
            actions.append("objective")
        if result.cleaned_up:
            actions.append("cleanup")
        if actions:
            parts.append(f"({', '.join(actions)})")
        if result.error is not None:
            parts.append(f"- {result.error}")
        click.echo(" ".join(parts))

    click.echo("")
    if failures == 0:
        click.echo(click.style(f"All {successes} branch(es) reconciled.", fg="green", bold=True))
    else:
        click.echo(
            click.style(f"{successes} succeeded, {failures} failed.", fg="yellow", bold=True)
        )
