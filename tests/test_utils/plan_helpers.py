"""Helpers for creating Plan and GitHubPlanStore objects in tests.

This module provides utilities for tests that need to set up plan state:
- make_test_plan(): Create Plan objects with sensible defaults
- plan_to_issue(): Convert Plan to IssueInfo for FakeGitHubIssues
- create_plan_store_with_plans(): Create GitHubPlanStore with FakeGitHubIssues
"""

from datetime import UTC, datetime

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_header_body
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState

# Fixed timestamp for deterministic tests
_DEFAULT_TIMESTAMP = datetime(2024, 1, 1, tzinfo=UTC)


def make_test_plan(
    plan_identifier: str | int,
    *,
    title: str | None = None,
    body: str = "",
    state: PlanState | None = None,
    url: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
    objective_issue: int | None = None,
) -> Plan:
    """Create a Plan with sensible test defaults.

    Args:
        plan_identifier: The plan ID (int or str). This is the only required param.
        title: Plan title. Defaults to "Test Plan {id}".
        body: Plan body. Defaults to empty string.
        state: Plan state. Defaults to OPEN.
        url: Plan URL. Defaults to GitHub-style URL pattern.
        labels: Plan labels. Defaults to ["erk-plan"].
        assignees: Plan assignees. Defaults to empty list.
        created_at: Creation timestamp. Defaults to 2024-01-01 UTC.
        updated_at: Update timestamp. Defaults to 2024-01-01 UTC.
        metadata: Provider-specific metadata. Defaults to {"number": <id>}.
        objective_issue: Objective issue number for linked plans.

    Returns:
        Plan with populated fields.
    """
    id_str = str(plan_identifier)
    id_int = int(plan_identifier)

    meta = metadata if metadata is not None else {"number": id_int}
    if objective_issue is not None:
        meta = {**meta, "objective_issue": objective_issue}

    return Plan(
        plan_identifier=id_str,
        title=title if title is not None else f"Test Plan {id_str}",
        body=body,
        state=state if state is not None else PlanState.OPEN,
        url=url if url is not None else f"https://github.com/owner/repo/issues/{id_str}",
        labels=labels if labels is not None else ["erk-plan"],
        assignees=assignees if assignees is not None else [],
        created_at=created_at if created_at is not None else _DEFAULT_TIMESTAMP,
        updated_at=updated_at if updated_at is not None else _DEFAULT_TIMESTAMP,
        metadata=meta,
    )


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert a Plan to IssueInfo for FakeGitHubIssues.

    This is useful when tests need to set up FakeGitHubIssues directly
    with Plan objects created via make_test_plan().

    Note: author defaults to "test-user" to match FakeGitHub's default
    auth_username, which is important for tests that use creator filtering.

    Args:
        plan: Plan to convert

    Returns:
        IssueInfo with equivalent data
    """
    # Map PlanState to GitHub state string
    state = "OPEN" if plan.state == PlanState.OPEN else "CLOSED"

    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state=state,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.astimezone(UTC),
        updated_at=plan.updated_at.astimezone(UTC),
        author="test-user",  # Matches FakeGitHub's default auth_username
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
    issues = {int(id): plan_to_issue(plan) for id, plan in plans.items()}
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
        source_repo=source_repo,
        objective_issue=objective_issue,
        created_from_session=created_from_session,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
    )
