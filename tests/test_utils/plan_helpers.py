"""Helpers for creating GitHubPlanStore with Plan objects in tests.

This module provides utilities for tests that need to set up plan state.
It converts Plan objects to IssueInfo so tests can use GitHubPlanStore
backed by FakeGitHubIssues.
"""

from datetime import UTC

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_header_body
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState


def _plan_to_issue_info(plan: Plan) -> IssueInfo:
    """Convert a Plan to IssueInfo for FakeGitHubIssues.

    Args:
        plan: Plan to convert

    Returns:
        IssueInfo with equivalent data

    Note:
        For schema v2 plans where metadata['issue_body'] contains the full issue body
        with metadata blocks, we use that for the IssueInfo.body so that GitHubPlanStore
        can properly extract plan headers (including objective_issue) when it converts
        back to a Plan via _convert_to_plan().
    """
    # Map PlanState to GitHub state string
    state = "OPEN" if plan.state == PlanState.OPEN else "CLOSED"

    # Use original issue body from metadata if available (schema v2)
    # Otherwise fall back to plan.body (schema v1 or tests without metadata)
    raw_issue_body = plan.metadata.get("issue_body") if plan.metadata else None
    body = raw_issue_body if isinstance(raw_issue_body, str) else plan.body

    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=body,
        state=state,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.astimezone(UTC),
        updated_at=plan.updated_at.astimezone(UTC),
        author="test-author",
    )


def create_plan_store_with_plans(
    plans: dict[str, Plan],
) -> tuple[GitHubPlanStore, FakeGitHubIssues]:
    """Create GitHubPlanStore backed by FakeGitHubIssues.

    This helper converts Plan objects to IssueInfo so tests can continue
    constructing Plan objects while using GitHubPlanStore internally.

    Args:
        plans: Mapping of plan_identifier -> Plan

    Returns:
        Tuple of (store, fake_issues) for test assertions.
        The fake_issues object provides mutation tracking like:
        - fake_issues.closed_issues: list of issue numbers that were closed
        - fake_issues.added_comments: list of (issue_number, body, comment_id) tuples
    """
    issues = {int(id): _plan_to_issue_info(plan) for id, plan in plans.items()}
    fake_issues = FakeGitHubIssues(issues=issues)
    return GitHubPlanStore(fake_issues), fake_issues


def format_plan_header_body_for_test(
    *,
    created_at: str = "2024-01-15T10:30:00Z",
    created_by: str = "test-user",
    worktree_name: str | None = None,
    branch_name: str | None = None,
    plan_comment_id: int | None = None,
    last_dispatched_run_id: str | None = None,
    last_dispatched_node_id: str | None = None,
    last_dispatched_at: str | None = None,
    last_local_impl_at: str | None = None,
    last_local_impl_event: str | None = None,
    last_local_impl_session: str | None = None,
    last_local_impl_user: str | None = None,
    last_remote_impl_at: str | None = None,
    last_remote_impl_run_id: str | None = None,
    last_remote_impl_session_id: str | None = None,
    source_repo: str | None = None,
    objective_issue: int | None = None,
    created_from_session: str | None = None,
    last_learn_session: str | None = None,
    last_learn_at: str | None = None,
) -> str:
    """Create plan header body for testing with sensible defaults."""
    return format_plan_header_body(
        created_at=created_at,
        created_by=created_by,
        worktree_name=worktree_name,
        branch_name=branch_name,
        plan_comment_id=plan_comment_id,
        last_dispatched_run_id=last_dispatched_run_id,
        last_dispatched_node_id=last_dispatched_node_id,
        last_dispatched_at=last_dispatched_at,
        last_local_impl_at=last_local_impl_at,
        last_local_impl_event=last_local_impl_event,
        last_local_impl_session=last_local_impl_session,
        last_local_impl_user=last_local_impl_user,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=last_remote_impl_run_id,
        last_remote_impl_session_id=last_remote_impl_session_id,
        source_repo=source_repo,
        objective_issue=objective_issue,
        created_from_session=created_from_session,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
    )
