"""Address PR review comments with AI-powered resolution.

This command addresses PR review comments locally using Claude CLI.
For remote resolution via GitHub Actions, use `erk workflow run pr-address`.
"""

import click

from erk.cli.ensure import Ensure
from erk.cli.output import stream_command_with_feedback
from erk.core.context import ErkContext


@click.command("address")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def address(ctx: ErkContext, *, dangerous: bool) -> None:
    """Address PR review comments with AI-powered resolution.

    Addresses PR review comments on the current branch using Claude.

    For remote resolution via GitHub Actions workflow, use:

    \b
      erk workflow run pr-address --pr <number>

    Examples:

    \b
      # Address comments locally with Claude
      erk pr address --dangerous
    """
    # Runtime validation: require --dangerous
    if not dangerous:
        raise click.UsageError("Missing option '--dangerous'.")

    cwd = ctx.cwd

    # Check Claude availability
    executor = ctx.claude_executor
    Ensure.invariant(
        executor.is_claude_available(),
        "Claude CLI is required for addressing PR comments.\n\n"
        "Install from: https://claude.com/download",
    )

    click.echo(click.style("Invoking Claude to address PR comments...", fg="yellow"))

    # Execute PR address command via Claude
    result = stream_command_with_feedback(
        executor=executor,
        command="/erk:pr-address",
        worktree_path=cwd,
        dangerous=True,
    )

    if not result.success:
        raise click.ClickException(result.error_message or "PR comment addressing failed")

    click.echo(click.style("\n\u2705 PR comments addressed!", fg="green", bold=True))
