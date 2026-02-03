"""Launch Claude to create a plan from an objective step."""

import click

from erk.cli.alias import alias
from erk.core.context import ErkContext
from erk_shared.context.types import InteractiveClaudeConfig


@alias("np")
@click.command("next-plan")
@click.argument("issue_ref")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    default=False,
    help="Allow dangerous permissions by passing --allow-dangerously-skip-permissions to Claude",
)
@click.pass_obj
def next_plan(ctx: ErkContext, issue_ref: str, dangerous: bool) -> None:
    """Create an implementation plan from an objective step.

    ISSUE_REF is an objective issue number or GitHub URL.

    This command launches Claude in plan mode (--permission-mode plan) to
    create an implementation plan from an objective step. The permission
    mode and other settings are configured via [interactive-claude] in
    ~/.erk/config.toml.
    """
    # Build command with argument
    command = f"/erk:objective-next-plan {issue_ref}"

    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ic_config = InteractiveClaudeConfig.default()
    else:
        ic_config = ctx.global_config.interactive_claude
    if dangerous:
        allow_dangerous_override = True
    else:
        allow_dangerous_override = None

    config = ic_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=allow_dangerous_override,
    )

    # Replace current process with Claude
    ctx.claude_launcher.launch_interactive(config, command=command)
