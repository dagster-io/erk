"""Reconcile auto-advance objectives."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.context.types import RepoContext
from erk_shared.objectives.reconciler import determine_action, execute_action


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

        mode_prefix = "[DRY RUN] " if dry_run else ""
        click.echo(f"{mode_prefix}Reconciling auto-advance objectives...\n", err=True)

    # Build Rich table with columns from plan
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Title", no_wrap=False)
    table.add_column("Action", no_wrap=True)
    table.add_column("Step", no_wrap=True)
    if dry_run:
        table.add_column("Reason", no_wrap=False)
    else:
        table.add_column("Result", no_wrap=False)

    plan_count = 0
    created_plans: list[int] = []
    errors: list[tuple[int, str]] = []

    for issue in issues:
        action = determine_action(ctx.prompt_executor, issue.body)

        step_display = action.step_id if action.step_id else "-"
        action_style = ""
        result_text = action.reason  # Default for dry-run

        if action.action_type == "create_plan":
            action_style = "green"
            plan_count += 1

            if not dry_run:
                # Execute the action
                exec_result = execute_action(
                    action,
                    github_issues=ctx.github.issues,
                    repo_root=repo.root,
                    prompt_executor=ctx.prompt_executor,
                    objective_number=issue.number,
                    objective_body=issue.body,
                )

                if exec_result.success:
                    plan_num = exec_result.plan_issue_number
                    created_plans.append(plan_num) if plan_num else None
                    result_text = f"Created plan #{plan_num}"
                    action_style = "green"
                else:
                    errors.append((issue.number, exec_result.error or "Unknown error"))
                    result_text = f"FAILED: {exec_result.error}"
                    action_style = "red"
                    # If plan was created but roadmap update failed, still track it
                    if exec_result.plan_issue_number:
                        created_plans.append(exec_result.plan_issue_number)

        elif action.action_type == "error":
            action_style = "red"
            if not dry_run:
                errors.append((issue.number, action.reason))

        table.add_row(
            f"#{issue.number}",
            issue.title,
            f"[{action_style}]{action.action_type}[/{action_style}]"
            if action_style
            else action.action_type,
            step_display,
            result_text,
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)

    # Summary line
    if dry_run:
        if plan_count > 0:
            click.echo(
                f"\n[DRY RUN] Would create {plan_count} plan(s). Run without --dry-run to execute.",
                err=True,
            )
        else:
            click.echo("\nNo actions needed.", err=True)
    else:
        # Live execution summary
        if created_plans:
            plan_refs = ", ".join(f"#{p}" for p in created_plans)
            click.echo(f"\nCreated {len(created_plans)} plan(s): {plan_refs}", err=True)
        elif plan_count == 0:
            click.echo("\nNo actions needed.", err=True)

        if errors:
            click.echo(f"\n{len(errors)} error(s) occurred:", err=True)
            for obj_num, err_msg in errors:
                click.echo(f"  - Objective #{obj_num}: {err_msg}", err=True)
            raise SystemExit(1)
