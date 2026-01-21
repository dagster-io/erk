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
from erk_shared.learn.trigger_async import (
    TriggerAsyncLearnNoSessionData,
    TriggerAsyncLearnNotErkPlan,
    TriggerAsyncLearnSuccess,
    trigger_async_learn_workflow,
)


@dataclass(frozen=True)
class ExecSuccessResponse:
    """Success response for exec script JSON output."""

    success: bool
    issue_number: int
    workflow_triggered: bool
    run_id: str


@dataclass(frozen=True)
class ExecErrorResponse:
    """Error response for exec script JSON output."""

    success: bool
    error: str


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

    result = trigger_async_learn_workflow(
        github=github,
        issues=github_issues,
        repo_root=repo_root,
        issue_number=issue_number,
        on_progress=None,
    )

    if isinstance(result, TriggerAsyncLearnNotErkPlan):
        error = ExecErrorResponse(
            success=False,
            error=f"Issue #{issue_number} is not an erk-plan",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    if isinstance(result, TriggerAsyncLearnNoSessionData):
        error = ExecErrorResponse(
            success=False,
            error="No session data available for learning",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    if isinstance(result, TriggerAsyncLearnSuccess):
        response = ExecSuccessResponse(
            success=True,
            issue_number=result.issue_number,
            workflow_triggered=True,
            run_id=result.run_id,
        )
        click.echo(json.dumps(asdict(response)))
        return

    # Should never reach here - exhaustive pattern matching
    msg = f"Unexpected result type: {type(result)}"
    raise RuntimeError(msg)
