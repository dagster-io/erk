"""Learn plan creation for the land command.

Handles creating erk-learn plans when a PR is landed.
Extracted to avoid circular imports between land_cmd and land_pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

from erk.core.context import ErkContext
from erk_shared.output.output import user_output
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.sessions.discovery import SessionsForPlan, get_readable_sessions

if TYPE_CHECKING:
    from pathlib import Path

    from erk.cli.commands.land_pipeline import LandState


def _should_create_learn_pr(ctx: ErkContext) -> bool:
    """Check config hierarchy to determine if learn plan should be created on land.

    Checks local_config first (repo or local override), falls back to global_config.
    """
    if ctx.local_config.prompt_learn_on_land is not None:
        return ctx.local_config.prompt_learn_on_land
    if ctx.global_config is not None:
        return ctx.global_config.prompt_learn_on_land
    return True


def _create_learn_pr_with_sessions(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Create a learn plan as a draft PR with session info for the landed plan.

    This is a fire-and-forget operation that never blocks landing.
    Creates a draft PR with erk-learn label so the replan flow can pick it up.

    Args:
        ctx: ErkContext
        state: LandState with plan_id and merged_pr_number populated
    """
    if state.plan_id is None or state.merged_pr_number is None:
        return

    try:
        _create_learn_pr_impl(ctx, state=state)
    except Exception as exc:
        user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")


def _log_session_discovery(
    ctx: ErkContext,
    *,
    sessions: SessionsForPlan,
    all_session_ids: list[str],
) -> None:
    """Log session discovery summary with per-session type badges and sizes."""
    total = len(all_session_ids)
    if total == 0:
        user_output("  \u26a0\ufe0f  No sessions discovered for this plan")
        return

    n_planning = 1 if sessions.planning_session_id else 0
    n_impl = len(sessions.implementation_session_ids)
    n_learn = len(sessions.learn_session_ids)
    parts = f"{n_planning} planning, {n_impl} impl"
    if n_learn:
        parts += f", {n_learn} learn"
    user_output(f"  \U0001f4cb Discovered {total} session(s): {parts}")

    # Build readable lookup for O(1) per-session checks
    readable_map: dict[str, Path] = dict(get_readable_sessions(sessions, ctx.claude_installation))

    # Classify each session and emit a typed line
    planning_ids = {sessions.planning_session_id} if sessions.planning_session_id else set()
    impl_ids = set(sessions.implementation_session_ids)
    learn_ids = set(sessions.learn_session_ids)

    table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 1),
        pad_edge=False,
    )
    table.add_column("pad", width=5, no_wrap=True)
    table.add_column("emoji", no_wrap=True)
    table.add_column("label", no_wrap=True)
    table.add_column("session", no_wrap=True)
    table.add_column("detail", no_wrap=True)

    for sid in all_session_ids:
        if sid in planning_ids:
            emoji, label = "\U0001f4dd", "planning:"
        elif sid in impl_ids:
            emoji, label = "\U0001f527", "impl:"
        elif sid in learn_ids:
            emoji, label = "\U0001f4da", "learn:"
        else:
            emoji, label = "\u2753", "unknown:"

        if sid in readable_map:
            size_kb = readable_map[sid].stat().st_size // 1024
            detail = f"[dim](local, {size_kb:,} KB)[/dim]"
        else:
            detail = "[dim](not found)[/dim]"

        table.add_row("", emoji, label, f"{sid[:8]}...", detail)

    console = Console(stderr=True, force_terminal=True)
    console.print(table)


def _create_learn_pr_impl(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Inner implementation for learn plan creation (raises on error)."""
    plan_id = state.plan_id
    if plan_id is None:
        return

    # Check config
    if not _should_create_learn_pr(ctx):
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

    # Log session discovery summary
    _log_session_discovery(ctx, sessions=sessions, all_session_ids=all_session_ids)

    # Build learn plan body
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

    # Create the learn plan as a draft PR
    result = create_plan_draft_pr(
        git=ctx.git,
        github=ctx.github,
        github_issues=ctx.issues,
        branch_manager=ctx.branch_manager,
        time=ctx.time,
        repo_root=state.main_repo_root,
        cwd=state.cwd,
        plan_content=plan_content,
        title=f"Learn: {plan_result.title}",
        labels=["erk-pr", "erk-learn"],
        source_repo=None,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=int(plan_id),
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
