"""Address PR review comments with AI-powered resolution.

This command addresses PR review comments locally using Claude CLI.
For remote resolution via GitHub Actions, use `erk launch pr-address`.
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
    help="Force dangerous mode (skip permission prompts).",
)
@click.option(
    "--safe",
    is_flag=True,
    help="Disable dangerous mode (permission prompts enabled).",
)
@click.pass_obj
def address(ctx: ErkContext, *, dangerous: bool, safe: bool) -> None:
    """Address PR review comments with AI-powered resolution.

    Addresses PR review comments on the current branch using Claude.

    For remote resolution via GitHub Actions workflow, use:

    \b
      erk launch pr-address --pr <number>

    Examples:

    \b
      # Address comments locally with Claude (dangerous by default)
      erk pr address

    \b
      # Address in safe mode (permission prompts enabled)
      erk pr address --safe

    To disable dangerous mode by default:

    \b
      erk config set live_dangerously false
    """
    effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)

    cwd = ctx.cwd

    # Check Claude availability
    executor = ctx.prompt_executor
    Ensure.invariant(
        executor.is_available(),
        "Claude CLI is required for addressing PR comments.\n\n"
        "Install from: https://claude.com/download",
    )

    click.echo(click.style("Invoking Claude to address PR comments...", fg="yellow"))

    # Execute PR address command via Claude
    result = stream_command_with_feedback(
        executor=executor,
        command="/erk:pr-address",
        worktree_path=cwd,
        dangerous=effective_dangerous,
        permission_mode="edits",
    )

    if not result.success:
        raise click.ClickException(result.error_message or "PR comment addressing failed")

    click.echo(click.style("\n\u2705 PR comments addressed!", fg="green", bold=True))
