"""Learn plan creation for the land command.

Handles creating erk-learn plans when a PR is landed.
Extracted to avoid circular imports between land_cmd and land_pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from erk.core.context import ErkContext
from erk_shared.gateway.github.plan_issues import create_plan_issue
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound

if TYPE_CHECKING:
    from erk.cli.commands.land_pipeline import LandState


def _should_create_learn_issue(ctx: ErkContext) -> bool:
    """Check config hierarchy to determine if learn plan should be created on land.

    Checks local_config first (repo or local override), falls back to global_config.
    """
    if ctx.local_config.prompt_learn_on_land is not None:
        return ctx.local_config.prompt_learn_on_land
    if ctx.global_config is not None:
        return ctx.global_config.prompt_learn_on_land
    return True


def _create_learn_issue_with_sessions(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Create a learn plan with session info for the landed plan.

    This is a fire-and-forget operation that never blocks landing.
    Creates a plan with erk-learn label so the replan flow can pick it up.

    Args:
        ctx: ErkContext
        state: LandState with plan_id and merged_pr_number populated
    """
    if state.plan_id is None or state.merged_pr_number is None:
        return

    try:
        _create_learn_issue_impl(ctx, state=state)
    except Exception as exc:
        user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")


def _create_learn_issue_impl(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Inner implementation for learn plan creation (raises on error)."""
    plan_id = state.plan_id
    if plan_id is None:
        return

    # Check config
    if not _should_create_learn_issue(ctx):
        return

    # Fetch plan to check labels — skip learn plans (cycle prevention)
    plan_result = ctx.plan_store.get_plan(state.main_repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        return
    if "erk-learn" in plan_result.labels:
        return

    # Discover sessions for the plan
    sessions = ctx.plan_backend.find_sessions_for_plan(state.main_repo_root, plan_id)
    all_session_ids = sessions.all_session_ids()

    # Build learn issue body
    if all_session_ids:
        session_lines = [f"- `{sid}`" for sid in all_session_ids]
    else:
        session_lines = ["- (none)"]
    session_section = "\n".join(session_lines)
    plan_content = (
        f"# Learn: {plan_result.title}\n\n"
        f"Source plan: #{plan_id}\n"
        f"Merged PR: #{state.merged_pr_number}\n\n"
        f"## Sessions\n\n{session_section}"
    )

    # Create the learn plan
    result = create_plan_issue(
        github_issues=ctx.issues,
        repo_root=state.main_repo_root,
        plan_content=plan_content,
        title=f"Learn: {plan_result.title}",
        extra_labels=["erk-learn"],
        title_tag="[erk-learn]",
        source_repo=None,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=int(plan_id),
        lifecycle_stage="planned",
    )

    if result.success:
        user_output(
            click.style("✓", fg="green")
            + f" Created learn plan #{result.plan_number} for plan #{plan_id}"
        )
    elif result.error:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Learn plan creation failed: {result.error}"
        )
