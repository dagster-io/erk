"""Helpers for creating plan stores with Plan objects in tests.

This module provides utilities for tests that need to set up plan state.
It converts Plan objects to the appropriate backing store format:
- GitHubPlanStore backed by FakeGitHubIssues (GitHub Issues backend)
- DraftPRPlanBackend backed by FakeGitHub (Draft PR backend)

For dual-backend testing, use create_plan_store() which dispatches based
on a backend parameter.
"""

from datetime import UTC

from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.draft_pr_lifecycle import (
    DETAILS_CLOSE,
    DETAILS_OPEN,
    PLAN_CONTENT_SEPARATOR,
)
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import Plan, PlanState

_PLAN_HEADER_END_MARKER = "<!-- /erk:metadata-block:plan-header -->"


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


def _plan_to_pr_details(plan: Plan) -> PRDetails:
    """Convert a Plan to PRDetails for FakeGitHub.

    Handles two body formats:
    1. Body with plan-header metadata block: reformats into PR body format
       (metadata block + separator + plan content)
    2. Plain body without metadata: uses body directly as PR body

    Args:
        plan: Plan to convert

    Returns:
        PRDetails with equivalent data and a generated branch name
    """
    state = "OPEN" if plan.state == PlanState.OPEN else "CLOSED"
    branch_name = f"plan-{plan.plan_identifier}"

    # Build PR body: if the plan body has a metadata block, reformat it with separator
    # and wrap plan content in <details> tags (new lifecycle format)
    body = plan.body
    end_marker_idx = body.find(_PLAN_HEADER_END_MARKER)
    if end_marker_idx != -1:
        # Body contains a plan-header block - split into metadata and content parts
        metadata_part = body[: end_marker_idx + len(_PLAN_HEADER_END_MARKER)]
        content_part = body[end_marker_idx + len(_PLAN_HEADER_END_MARKER) :].strip()
        details_section = DETAILS_OPEN + content_part + DETAILS_CLOSE
        pr_body = metadata_part + PLAN_CONTENT_SEPARATOR + details_section
    else:
        pr_body = body

    # Include erk-plan label plus any existing labels
    labels = tuple(plan.labels) if "erk-plan" in plan.labels else ("erk-plan", *plan.labels)

    return PRDetails(
        number=int(plan.plan_identifier),
        url=plan.url,
        title=plan.title,
        body=pr_body,
        state=state,
        is_draft=True,
        base_ref_name="main",
        head_ref_name=branch_name,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=labels,
    )


def create_draft_pr_store_with_plans(
    plans: dict[str, Plan],
) -> tuple[DraftPRPlanBackend, FakeGitHub]:
    """Create DraftPRPlanBackend backed by FakeGitHub.

    This helper converts Plan objects to PRDetails so tests can continue
    constructing Plan objects while using DraftPRPlanBackend internally.

    Args:
        plans: Mapping of plan_identifier -> Plan

    Returns:
        Tuple of (backend, fake_github) for test assertions.
        The fake_github object provides mutation tracking like:
        - fake_github.closed_prs: list of PR numbers that were closed
        - fake_github.pr_comments: list of (pr_number, body) tuples
    """
    pr_details: dict[int, PRDetails] = {}
    prs: dict[str, PullRequestInfo] = {}
    pr_labels: dict[int, set[str]] = {}

    for plan_id, plan in plans.items():
        details = _plan_to_pr_details(plan)
        pr_number = int(plan_id)
        branch_name = details.head_ref_name

        pr_details[pr_number] = details
        prs[branch_name] = PullRequestInfo(
            number=pr_number,
            state=details.state,
            url=details.url,
            is_draft=True,
            title=details.title,
            checks_passing=None,
            owner=details.owner,
            repo=details.repo,
            head_branch=branch_name,
        )
        pr_labels[pr_number] = set(details.labels)

    fake_github = FakeGitHub(
        pr_details=pr_details,
        prs=prs,
    )
    # Set labels after construction (not a constructor param)
    for pr_number, labels in pr_labels.items():
        fake_github.set_pr_labels(pr_number, labels)

    return DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime()), fake_github


def create_plan_store(
    plans: dict[str, Plan],
    *,
    backend: str,
) -> tuple[PlanStore, FakeGitHubIssues | FakeGitHub]:
    """Create a plan store for the given backend type.

    Polymorphic dispatcher that creates the appropriate store type
    based on the backend parameter. Use in tests that opt into
    dual-backend testing via a plan_backend_type fixture.

    Args:
        plans: Mapping of plan_identifier -> Plan
        backend: Backend type - "github" or "draft_pr"

    Returns:
        Tuple of (store, fake) where fake is FakeGitHubIssues or FakeGitHub.
    """
    if backend == "draft_pr":
        return create_draft_pr_store_with_plans(plans)
    return create_plan_store_with_plans(plans)


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
    created_from_workflow_run_url: str | None = None,
    last_learn_session: str | None = None,
    last_learn_at: str | None = None,
    learn_status: str | None = None,
    learn_plan_issue: int | None = None,
    learn_plan_pr: int | None = None,
    learned_from_issue: int | None = None,
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
        created_from_workflow_run_url=created_from_workflow_run_url,
        last_learn_session=last_learn_session,
        last_learn_at=last_learn_at,
        learn_status=learn_status,
        learn_plan_issue=learn_plan_issue,
        learn_plan_pr=learn_plan_pr,
        learned_from_issue=learned_from_issue,
    )
