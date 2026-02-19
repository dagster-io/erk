"""Update objective after landing a PR.

Standalone exec script that calls Claude to update the linked objective
after a PR has been merged. Always exits 0 (fail-open) because the
landing has already succeeded.

Usage:
    erk exec objective-update-after-land --objective 42 --pr 123 --branch feature

Exit Codes:
    0: Always (fail-open - landing already succeeded)
"""

import click

from erk.cli.output import stream_command_with_feedback
from erk.core.context import ErkContext
from erk_shared.context.helpers import require_context
from erk_shared.output.output import user_output


def run_objective_update(
    ctx: ErkContext,
    *,
    objective: int,
    pr: int,
    branch: str,
) -> None:
    """Update objective after landing a PR.

    Calls Claude to update the linked objective with the landed PR information.
    Prints status messages but never raises — fail-open because the landing
    has already succeeded.
    """
    user_output(f"   Linked to Objective #{objective}")
    user_output("")
    user_output("Starting objective update...")

    cmd = (
        f"/erk:objective-update-with-landed-pr "
        f"--pr {pr} --objective {objective} --branch {branch} --auto-close"
    )

    result = stream_command_with_feedback(
        executor=ctx.prompt_executor,
        command=cmd,
        worktree_path=ctx.cwd,
        dangerous=True,
        permission_mode="edits",
    )

    if result.success:
        user_output("")
        user_output(click.style("✓", fg="green") + " Objective updated successfully")
    else:
        user_output("")
        user_output(
            click.style("⚠", fg="yellow") + f" Objective update failed: {result.error_message}"
        )
        user_output("  Run '/erk:objective-update-with-landed-pr' manually to retry")


@click.command(name="objective-update-after-land")
@click.option(
    "--objective",
    type=int,
    required=True,
    help="Linked objective issue number",
)
@click.option(
    "--pr",
    type=int,
    required=True,
    help="PR number that was just landed",
)
@click.option(
    "--branch",
    required=True,
    help="Branch name that was landed",
)
@click.pass_context
def objective_update_after_land(
    ctx: click.Context,
    *,
    objective: int,
    pr: int,
    branch: str,
) -> None:
    """Update objective after landing a PR.

    Calls Claude to update the linked objective with the landed PR information.
    Always exits 0 (fail-open) because the landing has already succeeded.
    """
    erk_ctx = require_context(ctx)
    run_objective_update(erk_ctx, objective=objective, pr=pr, branch=branch)
