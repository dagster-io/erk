"""Core operation for pr dispatch (transport-independent).

Contains the request type and operation function that both the
human command (dispatch/cli.py) and machine command (dispatch/json_cli.py) share.
"""

import logging
from dataclasses import dataclass
from typing import Any

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PR_TITLE_PREFIX,
)
from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_branch_name
from erk_shared.gateway.github.parsing import (
    construct_pr_url,
    construct_workflow_run_url,
)
from erk_shared.gateway.http.abc import HttpError
from erk_shared.impl_context import build_impl_context_files
from erk_shared.plan_store.planned_pr_lifecycle import extract_plan_content

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrDispatchRequest:
    """Request type for pr dispatch (single PR)."""

    pr_number: int
    base_branch: str | None
    ref: str | None


@dataclass(frozen=True)
class PrDispatchResult:
    """Result for erk json pr dispatch."""

    pr_number: int
    plan_title: str
    plan_url: str
    impl_pr_number: int | None
    impl_pr_url: str | None
    workflow_run_id: str
    workflow_url: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "plan_title": self.plan_title,
            "plan_url": self.plan_url,
            "impl_pr_number": self.impl_pr_number,
            "impl_pr_url": self.impl_pr_url,
            "workflow_run_id": self.workflow_run_id,
            "workflow_url": self.workflow_url,
        }


def run_pr_dispatch(
    ctx: ErkContext,
    request: PrDispatchRequest,
    *,
    owner: str,
    repo_name: str,
) -> PrDispatchResult | MachineCommandError:
    """Execute pr dispatch operation via RemoteGitHub (no local git required).

    Validates the PR, commits impl-context files, dispatches the workflow,
    and posts a queued event comment.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        owner: Repository owner
        repo_name: Repository name

    Returns:
        PrDispatchResult or MachineCommandError
    """
    remote = get_remote_github(ctx)
    pr_number = request.pr_number

    # Validate PR: fetch issue, check title prefix, check OPEN state
    issue = remote.get_issue(owner=owner, repo=repo_name, number=pr_number)
    if isinstance(issue, IssueNotFound):
        return MachineCommandError(
            error_type="not_found",
            message=f"PR #{pr_number} not found",
        )

    if not issue.title.startswith(ERK_PR_TITLE_PREFIX):
        return MachineCommandError(
            error_type="invalid_pr",
            message=(
                f"PR #{pr_number} does not have '[erk-pr]' title prefix. "
                "Cannot dispatch non-plan PRs for automated implementation."
            ),
        )

    if issue.state != "OPEN":
        return MachineCommandError(
            error_type="pr_not_open",
            message=(
                f"PR #{pr_number} is {issue.state}. "
                "Cannot dispatch closed PRs for automated implementation."
            ),
        )

    # Extract branch name from plan-header metadata
    branch_name = extract_plan_header_branch_name(issue.body) if issue.body else None
    if branch_name is None:
        return MachineCommandError(
            error_type="branch_not_determinable",
            message=(
                f"PR #{pr_number}: cannot determine branch name from plan metadata. "
                "The PR body must contain a plan-header metadata block with a branch_name field."
            ),
        )

    # Resolve base branch
    base_branch = (
        request.base_branch
        if request.base_branch is not None
        else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )

    # Get authenticated user
    submitted_by = remote.get_authenticated_user()

    # Fetch plan content from the PR body
    plan_content = extract_plan_content(issue.body) if issue.body else ""

    # Commit impl-context files to the plan branch via REST API
    now_iso = ctx.time.now().isoformat()
    files = build_impl_context_files(
        plan_content=plan_content,
        plan_id=str(pr_number),
        url=issue.url,
        provider="github-draft-pr",
        objective_id=None,
        now_iso=now_iso,
        node_ids=None,
    )
    for file_path, content in files.items():
        remote.create_file_commit(
            owner=owner,
            repo=repo_name,
            path=file_path,
            content=content,
            message=f"Add plan for PR #{pr_number}",
            branch=branch_name,
        )

    # Dispatch workflow
    queued_at = ctx.time.now().isoformat()
    dispatch_ref = (
        request.ref
        if request.ref is not None
        else remote.get_default_branch_name(owner=owner, repo=repo_name)
    )
    inputs = {
        "plan_id": str(pr_number),
        "submitted_by": submitted_by,
        "plan_title": issue.title,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "base_branch": base_branch,
        "plan_backend": "planned_pr",
    }
    run_id = remote.dispatch_workflow(
        owner=owner,
        repo=repo_name,
        workflow=DISPATCH_WORKFLOW_NAME,
        ref=dispatch_ref,
        inputs=inputs,
    )

    # Compute URLs
    workflow_url = construct_workflow_run_url(owner, repo_name, run_id)
    impl_pr_url = construct_pr_url(owner, repo_name, pr_number)

    # Update PR body with workflow run link (best-effort)
    try:
        if issue.body:
            updated_body = issue.body + f"\n\n**Workflow run:** {workflow_url}"
            remote.update_pull_request_body(
                owner=owner,
                repo=repo_name,
                pr_number=pr_number,
                body=updated_body,
            )
    except HttpError as e:
        logger.warning("Failed to update PR body with workflow run link: %s", e)

    # Post queued event comment (best-effort)
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            plan_number=pr_number,
            validation_results={
                "pr_is_open": True,
                "has_erk_pr_title": True,
            },
            expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
        )
        comment_body = render_erk_issue_event(
            title="Plan Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Plan submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                f"dispatched via remote dispatch.\n\n"
                f"**Workflow run:** {workflow_url}"
            ),
        )
        remote.add_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=pr_number,
            body=comment_body,
        )
    except HttpError as e:
        logger.warning("Failed to post queued comment: %s", e)

    return PrDispatchResult(
        pr_number=pr_number,
        plan_title=issue.title,
        plan_url=issue.url,
        impl_pr_number=pr_number,
        impl_pr_url=impl_pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )
