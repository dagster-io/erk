"""Shared helpers for objective tracking in land commands.

These helpers are used by `erk land` to check for linked objectives
and prompt users to update them after landing.
"""

import logging
from pathlib import Path

import click

from erk.cli.output import stream_command_with_feedback
from erk.core.context import ErkContext
from erk_shared.naming import extract_objective_number
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound, PlanState

logger = logging.getLogger(__name__)


def check_and_display_plan_issue_closure(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
) -> int | None:
    """Check and display plan issue closure status after landing.

    Since PRs no longer contain "Closes #N", this always closes the plan
    issue directly via the API.

    Returns the plan issue number if found, None otherwise.
    This is fail-open: returns None silently if the issue doesn't exist.
    """
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo_root, branch)
    if plan_id is None:
        return None

    plan_number = int(plan_id)

    result = ctx.plan_store.get_plan(repo_root, plan_id)
    if isinstance(result, PlanNotFound):
        logger.debug("Plan issue #%d not found, skipping closure check", plan_number)
        return None

    if result.state == PlanState.CLOSED:
        user_output(click.style("✓", fg="green") + f" Closed plan issue #{plan_number}")
        return plan_number

    # Issue is open — close it directly (no more "Closes #N" auto-close)
    ctx.plan_store.close_plan(repo_root, plan_id)
    user_output(click.style("✓", fg="green") + f" Closed plan issue #{plan_number}")

    return plan_number


def get_objective_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> int | None:
    """Extract objective issue number from branch's linked plan issue.

    Returns objective issue number if:
    1. Branch is associated with a plan with objective_id in metadata, OR
    2. Branch name encodes the objective number (fallback)

    Returns None otherwise (fail-open - never blocks landing).
    """
    try:
        result = ctx.plan_backend.get_plan_for_branch(repo_root, branch)
    except RuntimeError:
        return extract_objective_number(branch)
    if isinstance(result, PlanNotFound):
        return extract_objective_number(branch)
    if result.objective_id is not None:
        return result.objective_id
    return extract_objective_number(branch)


def run_objective_update_after_close(
    ctx: ErkContext,
    *,
    plan_number: int,
    objective: int,
) -> None:
    """Run the objective update after a plan has been closed.

    This is fail-open: catches all errors and never raises, because the
    plan closing has already succeeded by the time this runs.
    """
    user_output(f"   Linked to Objective #{objective}")
    user_output("")
    user_output("Starting objective update...")

    cmd = f"/erk:objective-update-with-closed-plan --plan {plan_number} --objective {objective}"

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
        user_output("  Run '/erk:objective-update-with-closed-plan' manually to retry")


def run_objective_update_after_land(
    ctx: ErkContext,
    *,
    objective: int,
    pr: int,
    branch: str,
    plan: int | None,
    worktree_path: Path,
) -> None:
    """Run the objective update after a PR has been landed.

    This is fail-open: catches all errors and never raises, because the
    landing has already succeeded by the time this runs.
    """
    user_output(f"   Linked to Objective #{objective}")
    user_output("")
    user_output("Starting objective update...")

    plan_arg = f" --plan {plan}" if plan is not None else ""
    cmd = (
        f"/erk:objective-update-with-landed-pr "
        f"--pr {pr} --objective {objective} --branch {branch}{plan_arg} --auto-close"
    )

    result = stream_command_with_feedback(
        executor=ctx.prompt_executor,
        command=cmd,
        worktree_path=worktree_path,
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
