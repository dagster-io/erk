"""Helpers for PR dispatch metadata updates.

This module extracts shared logic for updating PR dispatch metadata
when triggering remote workflows on branches that follow the plnd/ prefix pattern.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk_shared.output.output import user_output
from erk_shared.pr_store.backend import ManagedPrBackend
from erk_shared.pr_store.types import PrNotFound

if TYPE_CHECKING:
    from erk.core.context import ErkContext
    from erk.core.repo_discovery import RepoContext
    from erk_shared.gateway.github.abc import LocalGitHub


def write_dispatch_metadata(
    *,
    pr_backend: ManagedPrBackend,
    github: LocalGitHub,
    repo_root: Path,
    pr_number: int,
    run_id: str,
    dispatched_at: str,
) -> None:
    """Resolve node_id and write dispatch metadata to PR header.

    Raises:
        RuntimeError: If PR not found or node_id unavailable.
    """
    node_id = github.get_workflow_run_node_id(repo_root, run_id)
    if node_id is None:
        raise RuntimeError(f"Could not get node_id for run {run_id}")

    # LBYL: Check PR exists before updating metadata
    pr_id = str(pr_number)
    plan_result = pr_backend.get_managed_pr(repo_root, pr_id)
    if isinstance(plan_result, PrNotFound):
        raise RuntimeError(f"PR #{pr_number} not found")

    pr_backend.ensure_plan_header(repo_root, pr_id)
    pr_backend.update_metadata(
        repo_root,
        pr_id,
        {
            "last_dispatched_run_id": run_id,
            "last_dispatched_node_id": node_id,
            "last_dispatched_at": dispatched_at,
        },
    )


def maybe_update_pr_dispatch_metadata(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    run_id: str,
) -> None:
    """Update PR dispatch metadata if branch follows P{plan}-pattern.

    This function is used after triggering a remote workflow to record dispatch
    metadata (run_id, node_id, timestamp) on the associated PR.

    If the PR lacks a plan-header metadata block, one is automatically created
    before writing dispatch metadata. This handles PRs created through
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
    pr_id = ctx.pr_backend.resolve_pr_number_for_branch(repo.root, branch_name)
    if pr_id is None:
        return

    node_id = ctx.github.get_workflow_run_node_id(repo.root, run_id)
    if node_id is None:
        return

    ctx.pr_backend.ensure_plan_header(repo.root, pr_id)
    ctx.pr_backend.update_metadata(
        repo.root,
        pr_id,
        {
            "last_dispatched_run_id": run_id,
            "last_dispatched_node_id": node_id,
            "last_dispatched_at": ctx.time.now().isoformat(),
        },
    )
    user_output(click.style("\u2713", fg="green") + f" Updated dispatch metadata on PR #{pr_id}")
