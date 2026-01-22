"""Launch Claude to replan an existing erk-plan issue."""

import os
import shutil

import click

from erk.core.context import ErkContext
from erk.core.interactive_claude import build_claude_args
from erk_shared.context.types import InteractiveClaudeConfig


@click.command("replan")
@click.argument("issue_ref")
@click.pass_obj
def replan_plan(ctx: ErkContext, issue_ref: str) -> None:
    """Replan an existing erk-plan issue against current codebase state.

    ISSUE_REF is an issue number or GitHub URL.

    This command launches Claude in plan mode to re-evaluate an existing
    plan against the current codebase, creating a fresh plan that incorporates
    any changes. The original issue is closed after the new plan is created.

    Examples:
        erk plan replan 2521
        erk plan replan https://github.com/owner/repo/issues/2521
    """
    # Verify Claude CLI is available
    if shutil.which("claude") is None:
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ic_config = InteractiveClaudeConfig.default()
    else:
        ic_config = ctx.global_config.interactive_claude
    config = ic_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    # Build Claude CLI arguments
    cmd_args = build_claude_args(config, command=f"/erk:replan {issue_ref}")

    # Replace current process with Claude
    os.execvp("claude", cmd_args)
