"""Reconcile auto-advance objectives."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.context.types import RepoContext
from erk_shared.objectives.reconciler import determine_action


@alias("rec")
@click.command("reconcile")
@click.option("--dry-run", is_flag=True, help="Show planned actions without executing")
@click.option(
    "--objective",
    "-o",
    type=int,
    help="Target a specific objective by issue number",
)
@click.pass_obj
def reconcile_objectives(ctx: ErkContext, *, dry_run: bool, objective: int | None) -> None:
    """Reconcile auto-advance objectives (determine next actions)."""
    if not dry_run:
        click.echo(
            "Live execution not yet implemented. Please use --dry-run.",
            err=True,
        )
        raise SystemExit(1)

    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    if objective is not None:
        # Single objective mode - target specific issue
        if not ctx.github.issues.issue_exists(repo.root, objective):
            click.echo(f"Error: Issue #{objective} not found", err=True)
            raise SystemExit(1)
        issue = ctx.github.issues.get_issue(repo.root, objective)
        if "erk-objective" not in issue.labels:
            click.echo(f"Error: Issue #{objective} is not an erk-objective", err=True)
            raise SystemExit(1)
        issues = [issue]
        click.echo(f"Analyzing objective #{objective}...\n", err=True)
    else:
        # All auto-advance objectives (existing behavior)
        issues = ctx.github.issues.list_issues(
            repo_root=repo.root,
            labels=["erk-objective", "auto-advance"],
            state="open",
        )

        if not issues:
            click.echo("No auto-advance objectives found.", err=True)
            return

        click.echo("Reconciling auto-advance objectives...\n", err=True)

    # Build Rich table with columns from plan
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Title", no_wrap=False)
    table.add_column("Action", no_wrap=True)
    table.add_column("Step", no_wrap=True)
    table.add_column("Reason", no_wrap=False)

    plan_count = 0
    for issue in issues:
        action = determine_action(ctx.prompt_executor, issue.body)

        step_display = action.step_id if action.step_id else "-"
        action_style = ""
        if action.action_type == "create_plan":
            action_style = "green"
            plan_count += 1
        elif action.action_type == "error":
            action_style = "red"

        table.add_row(
            f"#{issue.number}",
            issue.title,
            f"[{action_style}]{action.action_type}[/{action_style}]"
            if action_style
            else action.action_type,
            step_display,
            action.reason,
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)

    # Summary line
    if plan_count > 0:
        click.echo(
            f"\n[DRY RUN] Would create {plan_count} plan(s). Run without --dry-run to execute.",
            err=True,
        )
    else:
        click.echo("\nNo actions needed.", err=True)
