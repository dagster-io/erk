"""Cancel a workflow run command."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("cancel")
@click.argument("run_id")
@click.pass_obj
def cancel_run(ctx: ErkContext, run_id: str) -> None:
    """Cancel an in-progress or queued workflow run."""
    Ensure.gh_authenticated(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)

    ctx.github.cancel_workflow_run(repo.root, run_id)
    user_output(f"Cancelled workflow run {click.style(run_id, fg='cyan')}")
