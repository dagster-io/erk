"""Rebase PR onto base branch with AI-powered conflict resolution.

This command rebases the current branch locally using Claude CLI.
For remote rebase via GitHub Actions, use `erk launch pr-rebase`.
"""

import click

from erk.cli.ensure import Ensure
from erk.cli.output import stream_rebase
from erk.core.context import ErkContext


@click.command("rebase")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def rebase(ctx: ErkContext, *, dangerous: bool) -> None:
    """Rebase PR onto base branch with AI-powered conflict resolution.

    Rebases the current branch and resolves any merge conflicts using Claude.
    Does not require or interact with Graphite stacks.

    Also works when a rebase is already in progress with unresolved conflicts.
    If you started a rebase manually and hit conflicts you can't resolve, run
    this command to have Claude pick up where you left off.

    For remote rebase via GitHub Actions workflow, use:

    \b
      erk launch pr-rebase [--pr <number>]

    Examples:

    \b
      # Rebase locally with Claude
      erk pr rebase --dangerous

    \b
      # Resume a rebase that stopped on conflicts
      git rebase main          # hits conflicts
      erk pr rebase --dangerous  # Claude resolves them

    To disable the --dangerous flag requirement:

    \b
      erk config set require_dangerous_flag_for_implicitly_dangerous_operations false
    """
    Ensure.dangerous_flag(ctx, dangerous=dangerous)

    cwd = ctx.cwd

    # Check Claude availability
    executor = ctx.prompt_executor
    Ensure.invariant(
        executor.is_available(),
        "Claude CLI is required for rebase with conflict resolution.\n\n"
        "Install from: https://claude.com/download",
    )

    click.echo(
        click.style(
            "Rebasing with AI-powered conflict resolution...",
            fg="yellow",
        )
    )

    # Execute rebase with conflict resolution
    result = stream_rebase(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Rebase failed")

    click.echo(click.style("\n\u2705 Rebase complete!", fg="green", bold=True))
