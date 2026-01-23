"""Launch Claude to replan existing erk-plan issue(s)."""

import os
import shutil

import click

from erk.core.context import ErkContext
from erk.core.interactive_claude import build_claude_args
from erk_shared.context.types import InteractiveClaudeConfig


@click.command("replan")
@click.argument("issue_refs", nargs=-1, required=True)
@click.pass_obj
def replan_plan(ctx: ErkContext, issue_refs: tuple[str, ...]) -> None:
    """Replan existing erk-plan issue(s) against current codebase state.

    ISSUE_REFS are issue numbers or GitHub URLs. Multiple refs can be provided
    to consolidate plans into a single unified plan.

    This command launches Claude in plan mode to re-evaluate existing plan(s)
    against the current codebase, creating a fresh plan that incorporates
    any changes. Original issues are closed after the new plan is created.

    Examples:
        erk plan replan 2521
        erk plan replan https://github.com/owner/repo/issues/2521
        erk plan replan 123 456 789  # Consolidate multiple plans
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

    # Build Claude CLI arguments with space-separated issue refs
    refs_str = " ".join(issue_refs)
    cmd_args = build_claude_args(config, command=f"/erk:replan {refs_str}")

    # Replace current process with Claude
    os.execvp("claude", cmd_args)
