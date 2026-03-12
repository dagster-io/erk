"""Address PR review comments with AI-powered resolution.

This command addresses PR review comments locally using Claude CLI.
For remote resolution via GitHub Actions, use `erk launch pr-address`.
"""

import click

from erk.core.context import ErkContext
from erk_shared.context.types import InteractiveAgentConfig


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
    if dangerous and safe:
        raise click.UsageError("--dangerous and --safe are mutually exclusive")

    # Get interactive agent config
    if ctx.global_config is None:
        ia_config = InteractiveAgentConfig.default()
    else:
        ia_config = ctx.global_config.interactive_agent

    # Map flags to config overrides
    if dangerous:
        config = ia_config.with_overrides(
            permission_mode_override="edits",
            model_override=None,
            dangerous_override=True,
            allow_dangerous_override=None,
        )
    elif safe:
        config = ia_config.with_overrides(
            permission_mode_override="safe",
            model_override=None,
            dangerous_override=None,
            allow_dangerous_override=None,
        )
    else:
        # Default: edits mode, allow dangerous when live_dangerously is set
        live_dangerously = (
            ctx.global_config.live_dangerously if ctx.global_config is not None else True
        )
        config = ia_config.with_overrides(
            permission_mode_override="edits",
            model_override=None,
            dangerous_override=None,
            allow_dangerous_override=True if live_dangerously else None,
        )

    # Replace current process with Claude
    try:
        ctx.agent_launcher.launch_interactive(config, command="/erk:pr-address")
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
