"""Launch Claude to create a plan from an objective step."""

import os
import shutil

import click

from erk.cli.alias import alias
from erk.core.context import ErkContext
from erk.core.interactive_claude import build_claude_args
from erk_shared.context.types import InteractiveClaudeConfig


@alias("np")
@click.command("next-plan")
@click.argument("issue_ref")
@click.pass_obj
def next_plan(ctx: ErkContext, issue_ref: str) -> None:
    """Create an implementation plan from an objective step.

    ISSUE_REF is an objective issue number or GitHub URL.

    This command launches Claude in plan mode (--permission-mode plan) to
    create an implementation plan from an objective step. The permission
    mode and other settings are configured via [interactive-claude] in
    ~/.erk/config.toml.
    """
    # Verify Claude CLI is available
    if shutil.which("claude") is None:
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    # Build command with argument
    command = f"/erk:objective-next-plan {issue_ref}"

    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ic_config = InteractiveClaudeConfig.default()
    else:
        ic_config = ctx.global_config.interactive_claude
    config = ic_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
    )

    # Build Claude CLI arguments
    cmd_args = build_claude_args(config, command=command)

    # Replace current process with Claude
    os.execvp("claude", cmd_args)
