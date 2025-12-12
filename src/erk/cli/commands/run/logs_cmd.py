"""View workflow run logs command."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("logs")
@click.argument("run_id", required=False)
@click.pass_obj
def logs_run(ctx: ErkContext, run_id: str | None) -> None:
    """View logs for a workflow run.

    If RUN_ID is not provided, shows logs for the most recent run
    on the current branch.
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    if run_id is None:
        # Auto-detect: find most recent run for current branch
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd), "Could not determine current branch"
        )

        runs = ctx.github.list_workflow_runs(repo.root, "implement-plan.yml", limit=50)
        branch_runs = [r for r in runs if r.branch == current_branch]

        if not branch_runs:
            user_output(
                f"No workflow runs found for branch: {click.style(current_branch, fg='yellow')}"
            )
            raise SystemExit(1)

        # Most recent is first (list_workflow_runs returns newest first)
        run_id = branch_runs[0].run_id
        user_output(
            f"Showing logs for run {click.style(run_id, fg='cyan')} "
            f"on branch {click.style(current_branch, fg='yellow')}\n"
        )

    try:
        log_output = ctx.github.get_run_logs(repo.root, run_id)
        # Direct output - logs go to stdout for piping
        click.echo(log_output)
    except RuntimeError as e:
        click.echo(click.style("Error: ", fg="red") + str(e), err=True)
        raise SystemExit(1) from None
