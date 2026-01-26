"""Helpers for plan dispatch metadata updates.

This module extracts shared logic for updating plan issue dispatch metadata
when triggering remote workflows on branches that follow the P{issue}-pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.plan_header import update_plan_header_dispatch
from erk_shared.gateway.github.types import BodyText
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_output

if TYPE_CHECKING:
    from erk.core.context import ErkContext
    from erk.core.repo_discovery import RepoContext


def maybe_update_plan_dispatch_metadata(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    run_id: str,
) -> None:
    """Update plan issue dispatch metadata if branch follows P{issue}-pattern.

    This function is used after triggering a remote workflow to record dispatch
    metadata (run_id, node_id, timestamp) on the associated plan issue.

    Uses early returns to skip updates when:
    - Branch doesn't match P{issue_number} pattern
    - Workflow run node ID is not available
    - Issue doesn't have a plan-header metadata block

    Args:
        ctx: Erk context with gateways
        repo: Repository context with root path
        branch_name: Branch name to extract issue number from
        run_id: Workflow run ID from trigger response
    """
    plan_issue_number = extract_leading_issue_number(branch_name)
    if plan_issue_number is None:
        return

    node_id = ctx.github.get_workflow_run_node_id(repo.root, run_id)
    if node_id is None:
        return

    plan_issue = ctx.issues.get_issue(repo.root, plan_issue_number)
    # LBYL: Check if plan-header block exists before attempting update
    # This is expected to be missing for non-erk-plan issues that happen
    # to have P{number} prefix in their branch name
    if find_metadata_block(plan_issue.body, "plan-header") is None:
        return

    updated_body = update_plan_header_dispatch(
        issue_body=plan_issue.body,
        run_id=run_id,
        node_id=node_id,
        dispatched_at=ctx.time.now().isoformat(),
    )
    ctx.issues.update_issue_body(repo.root, plan_issue_number, BodyText(content=updated_body))
    user_output(
        click.style("\u2713", fg="green")
        + f" Updated dispatch metadata on plan #{plan_issue_number}"
    )
