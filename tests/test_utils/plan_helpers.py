"""Helpers for creating GitHubPlanStore with Plan objects in tests.

This module provides utilities for tests that need to set up plan state.
It converts Plan objects to IssueInfo so tests can use GitHubPlanStore
backed by FakeGitHubIssues.
"""

from datetime import UTC

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState


def _plan_to_issue_info(plan: Plan) -> IssueInfo:
    """Convert a Plan to IssueInfo for FakeGitHubIssues.

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
