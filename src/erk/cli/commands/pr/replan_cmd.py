"""Launch Claude to replan existing plan(s)."""

import click

from erk.core.context import ErkContext
from erk_shared.context.types import InteractiveAgentConfig


@click.command("replan")
@click.argument("plan_refs", nargs=-1, required=True)
@click.pass_obj
def pr_replan(ctx: ErkContext, plan_refs: tuple[str, ...]) -> None:
    """Replan existing plan(s) against current codebase state.

    PLAN_REFS are plan numbers or GitHub URLs. Multiple refs can be provided
    to consolidate plans into a single unified plan.

    This command launches Claude in plan mode to re-evaluate existing plan(s)
    against the current codebase, creating a fresh plan that incorporates
    any changes. Original plans are closed after the new plan is created.

    Examples:
        erk pr replan 2521
        erk pr replan https://github.com/owner/repo/issues/2521
        erk pr replan 123 456 789  # Consolidate multiple plans
    """
    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ia_config = InteractiveAgentConfig.default()
    else:
        ia_config = ctx.global_config.interactive_agent
    config = ia_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    # Replace current process with Claude
    click.echo(f"Launching Claude to replan: {', '.join(plan_refs)}")
    command = f"/erk:replan {' '.join(plan_refs)}"
    try:
        ctx.agent_launcher.launch_interactive(config, command=command)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
