"""Helpers for creating plan stores with Plan objects in tests.

This module provides utilities for tests that need to set up plan state.
It converts Plan objects to PlannedPRBackend backed by FakeGitHub.
"""

from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import (
    DETAILS_CLOSE,
    DETAILS_OPEN,
    PLAN_CONTENT_SEPARATOR,
)
from erk_shared.plan_store.types import Plan, PlanState

_PLAN_HEADER_END_MARKER = "<!-- /erk:metadata-block:plan-header -->"


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
        pr_body = metadata_part + "\n\n" + details_section
    else:
        # Plain body without a plan-header block - synthesize one with branch_name so
        # PlannedPRBackend._convert_to_plan() can populate header_fields["branch_name"].
        # Real planned-PR plans always have branch_name in plan-header (set by plan_save).
        metadata_body = format_plan_header_body_for_test(branch_name=branch_name)
        details_section = DETAILS_OPEN + body + DETAILS_CLOSE
        pr_body = metadata_body + "\n\n" + details_section

    # Include erk-plan label plus any existing labels
    labels = tuple(plan.labels) if "erk-plan" in plan.labels else ("erk-plan", *plan.labels)

    # Use base_ref_name from plan metadata if provided, otherwise default to "main"
    raw_base_ref = plan.metadata.get("base_ref_name")
    base_ref = raw_base_ref if isinstance(raw_base_ref, str) else "main"

    return PRDetails(
        number=int(plan.plan_identifier),
        url=plan.url,
        title=plan.title,
        body=pr_body,
        state=state,
        is_draft=True,
        base_ref_name=base_ref,
        head_ref_name=branch_name,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=labels,
    )


def create_plan_store_with_plans(
    plans: dict[str, Plan],
) -> tuple[PlannedPRBackend, FakeGitHub]:
    """Create PlannedPRBackend backed by FakeGitHub.

    This helper converts Plan objects to PRDetails so tests can continue
    constructing Plan objects while using PlannedPRBackend internally.

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

    return PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime()), fake_github


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
    lifecycle_stage: str | None = None,
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
        lifecycle_stage=lifecycle_stage,
    )


def issue_info_to_pr_details(issue: IssueInfo) -> PRDetails:
    """Convert an IssueInfo to PRDetails for use with PlannedPRBackend.

    This helper converts IssueInfo test data to PRDetails for use with PlannedPRBackend.

    The PR body wraps the issue body in plan lifecycle format (details tags)
    if the body contains a plan-header metadata block.

    Args:
        issue: IssueInfo to convert

    Returns:
        PRDetails with equivalent data
    """
    body = issue.body
    end_marker_idx = body.find(_PLAN_HEADER_END_MARKER)
    if end_marker_idx != -1:
        metadata_part = body[: end_marker_idx + len(_PLAN_HEADER_END_MARKER)]
        content_part = body[end_marker_idx + len(_PLAN_HEADER_END_MARKER) :].strip()
        if content_part:
            details_section = DETAILS_OPEN + content_part + DETAILS_CLOSE
            pr_body = metadata_part + PLAN_CONTENT_SEPARATOR + details_section
        else:
            pr_body = metadata_part
    else:
        pr_body = body

    return PRDetails(
        number=issue.number,
        url=issue.url.replace("/issues/", "/pull/"),
        title=issue.title,
        body=pr_body,
        state=issue.state,
        is_draft=True,
        base_ref_name="main",
        head_ref_name=f"plan-{issue.number}",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=tuple(issue.labels),
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        author=issue.author,
    )


def create_backend_from_issues(
    issues: dict[int, IssueInfo],
) -> tuple[PlannedPRBackend, FakeGitHub, FakeGitHubIssues]:
    """Create a PlannedPRBackend from IssueInfo data.

    Migration helper: converts issue-based test data to PR-based data
    for PlannedPRBackend. The FakeGitHubIssues is also created so tests
    that need comment access (same API for PRs and issues) still work.

    Args:
        issues: Mapping of issue_number -> IssueInfo

    Returns:
        Tuple of (backend, fake_github, fake_issues)
    """
    pr_details: dict[int, PRDetails] = {}
    for num, issue in issues.items():
        pr_details[num] = issue_info_to_pr_details(issue)

    fake_issues = FakeGitHubIssues(issues=issues)
    fake_github = FakeGitHub(pr_details=pr_details, issues_gateway=fake_issues)
    backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
    return backend, fake_github, fake_issues
