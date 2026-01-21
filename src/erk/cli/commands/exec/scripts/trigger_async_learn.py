"""Trigger the async learn workflow for a plan issue.

This exec command dispatches the learn-dispatch.yml workflow for a given plan issue.
It validates the issue is an erk-plan and has session data available for learning.

Usage:
    erk exec trigger-async-learn <issue-number>

Output:
    JSON with success status and workflow dispatch info:
    {
        "success": true,
        "issue_number": 123,
        "workflow_triggered": true,
        "run_id": "12345678"
    }

Exit Codes:
    0: Success
    1: Error (issue not found, not an erk-plan, no session data, dispatch failed)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import (
    require_github,
    require_issues,
    require_repo_root,
)
from erk_shared.github.metadata.plan_header import (
    extract_plan_header_local_impl_session,
    extract_plan_header_remote_impl_run_id,
    update_plan_header_learn_status,
)


@dataclass(frozen=True)
class TriggerAsyncLearnSuccess:
    """Success response for async learn trigger."""

    success: bool
    issue_number: int
    workflow_triggered: bool
    run_id: str


@dataclass(frozen=True)
class TriggerAsyncLearnError:
    """Error response for async learn trigger."""

    success: bool
    error: str


def _has_session_data(issue_body: str) -> bool:
    """Check if plan issue has session data available for learning.

    Session data is available if either:
    1. last_remote_impl_run_id is set (remote workflow execution)
    2. last_local_impl_session is set (local implementation)

    Args:
        issue_body: Issue body containing plan-header block

    Returns:
        True if session data is available, False otherwise
    """
    remote_run_id = extract_plan_header_remote_impl_run_id(issue_body)
    if remote_run_id is not None:
        return True

    local_session = extract_plan_header_local_impl_session(issue_body)
    if local_session is not None:
        return True

    return False


@click.command(name="trigger-async-learn")
@click.argument("issue_number", type=int)
@click.pass_context
def trigger_async_learn(ctx: click.Context, issue_number: int) -> None:
    """Trigger async learn workflow for a plan issue.

    Validates the issue is an erk-plan with session data available,
    then dispatches the learn-dispatch.yml workflow.
    """
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch issue to validate it exists and is an erk-plan
    issue = github_issues.get_issue(repo_root, issue_number)

    # Validate erk-plan label
    if "erk-plan" not in issue.labels:
        error = TriggerAsyncLearnError(
            success=False,
            error=f"Issue #{issue_number} is not an erk-plan",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Validate session data availability
    if not _has_session_data(issue.body):
        error = TriggerAsyncLearnError(
            success=False,
            error="No session data available for learning",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Dispatch the learn-dispatch.yml workflow
    run_id = github.trigger_workflow(
        repo_root=repo_root,
        workflow="learn-dispatch.yml",
        inputs={"issue_number": str(issue_number)},
    )

    # Update plan header with learn_status=pending
    updated_body = update_plan_header_learn_status(
        issue_body=issue.body,
        learn_status="pending",
    )
    github_issues.update_issue_body(repo_root, issue_number, updated_body)

    # Output success
    result = TriggerAsyncLearnSuccess(
        success=True,
        issue_number=issue_number,
        workflow_triggered=True,
        run_id=run_id,
    )
    click.echo(json.dumps(asdict(result)))
