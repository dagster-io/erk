"""Helpers for plan dispatch metadata updates.

This module extracts shared logic for updating plan dispatch metadata
when triggering remote workflows on branches that follow the P{plan}-pattern.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk_shared.output.output import user_output
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import PlanNotFound

if TYPE_CHECKING:
    from erk.core.context import ErkContext
    from erk.core.repo_discovery import RepoContext
    from erk_shared.gateway.github.abc import LocalGitHub


def write_dispatch_metadata(
    *,
    plan_backend: PlanBackend,
    github: LocalGitHub,
    repo_root: Path,
    pr_number: int,
    run_id: str,
    dispatched_at: str,
) -> None:
    """Resolve node_id and write dispatch metadata to plan header.

    Raises:
        RuntimeError: If plan not found or node_id unavailable.
    """
    node_id = github.get_workflow_run_node_id(repo_root, run_id)
    if node_id is None:
        raise RuntimeError(f"Could not get node_id for run {run_id}")

    # LBYL: Check plan exists before updating metadata
    pr_id = str(pr_number)
    plan_result = plan_backend.get_plan(repo_root, pr_id)
    if isinstance(plan_result, PlanNotFound):
        raise RuntimeError(f"Plan #{pr_number} not found")

    plan_backend.ensure_plan_header(repo_root, pr_id)
    plan_backend.update_metadata(
        repo_root,
        pr_id,
        {
            "last_dispatched_run_id": run_id,
            "last_dispatched_node_id": node_id,
            "last_dispatched_at": dispatched_at,
        },
    )


def maybe_update_plan_dispatch_metadata(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    run_id: str,
) -> None:
    """Update plan dispatch metadata if branch follows P{plan}-pattern.

    This function is used after triggering a remote workflow to record dispatch
    metadata (run_id, node_id, timestamp) on the associated plan.

    If the plan lacks a plan-header metadata block, one is automatically created
    before writing dispatch metadata. This handles plans created through
    non-standard paths that bypass the normal create_plan() pipeline.

    Uses early returns to skip updates when:
    - Branch doesn't match P{plan_number} pattern
    - Workflow run node ID is not available

    Args:
        ctx: Erk context with gateways
        repo: Repository context with root path
        branch_name: Branch name to extract issue number from
        run_id: Workflow run ID from trigger response
    """
    pr_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
    if pr_id is None:
        return

    node_id = ctx.github.get_workflow_run_node_id(repo.root, run_id)
    if node_id is None:
        return

    ctx.plan_backend.ensure_plan_header(repo.root, pr_id)
    ctx.plan_backend.update_metadata(
        repo.root,
        pr_id,
        {
            "last_dispatched_run_id": run_id,
            "last_dispatched_node_id": node_id,
            "last_dispatched_at": ctx.time.now().isoformat(),
        },
    )
    user_output(click.style("\u2713", fg="green") + f" Updated dispatch metadata on plan #{pr_id}")
