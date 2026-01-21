"""Shared logic for triggering async learn workflow.

This module provides the core function for dispatching the learn-async.yml
workflow for a plan issue. It's used by both:
- `erk learn --async` command
- `erk exec trigger-async-learn` script
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.metadata.plan_header import (
    extract_plan_header_local_impl_session,
    extract_plan_header_remote_impl_run_id,
    update_plan_header_learn_status,
)


@dataclass(frozen=True)
class TriggerAsyncLearnSuccess:
    """Success result for async learn trigger."""

    issue_number: int
    run_id: str


@dataclass(frozen=True)
class TriggerAsyncLearnNotErkPlan:
    """Error: Issue is not an erk-plan."""

    issue_number: int


@dataclass(frozen=True)
class TriggerAsyncLearnNoSessionData:
    """Error: No session data available for learning."""

    issue_number: int


TriggerAsyncLearnResult = (
    TriggerAsyncLearnSuccess | TriggerAsyncLearnNotErkPlan | TriggerAsyncLearnNoSessionData
)


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
    if extract_plan_header_remote_impl_run_id(issue_body) is not None:
        return True

    if extract_plan_header_local_impl_session(issue_body) is not None:
        return True

    return False


def trigger_async_learn_workflow(
    *,
    github: GitHub,
    issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> TriggerAsyncLearnResult:
    """Trigger async learn workflow for a plan issue.

    Validates the issue is an erk-plan with session data available,
    dispatches learn-async.yml, and updates learn_status to pending.

    Args:
        github: GitHub gateway for workflow dispatch
        issues: GitHubIssues gateway for issue operations
        repo_root: Repository root directory
        issue_number: Plan issue number to learn from

    Returns:
        TriggerAsyncLearnSuccess on success, or an error result type
    """
    # Fetch issue to validate it exists and is an erk-plan
    issue = issues.get_issue(repo_root, issue_number)

    # Validate erk-plan label
    if "erk-plan" not in issue.labels:
        return TriggerAsyncLearnNotErkPlan(issue_number=issue_number)

    # Validate session data availability
    if not _has_session_data(issue.body):
        return TriggerAsyncLearnNoSessionData(issue_number=issue_number)

    # Dispatch the learn-async.yml workflow
    run_id = github.trigger_workflow(
        repo_root=repo_root,
        workflow="learn-async.yml",
        inputs={"issue_number": str(issue_number)},
    )

    # Update plan header with learn_status=pending
    updated_body = update_plan_header_learn_status(
        issue_body=issue.body,
        learn_status="pending",
    )
    issues.update_issue_body(repo_root, issue_number, updated_body)

    return TriggerAsyncLearnSuccess(issue_number=issue_number, run_id=run_id)
