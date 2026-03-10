"""Retry a workflow run command."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("retry")
@click.argument("run_id")
@click.option("--failed", is_flag=True, help="Only re-run failed jobs")
@click.pass_obj
def retry_run(ctx: ErkContext, run_id: str, failed: bool) -> None:
    """Retry a completed workflow run."""
    Ensure.gh_authenticated(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)

    ctx.github.rerun_workflow_run(repo.root, run_id, failed_only=failed)
    label = "failed jobs of " if failed else ""
    user_output(f"Retried {label}workflow run {click.style(run_id, fg='cyan')}")
