"""Intermediate representation types for plan command JSON output.

IR types are frozen dataclasses that represent clean, structured output data
with no Rich markup or click.style formatting. Builder functions convert from
domain types (PlanRowData, Plan) to these IR types.

Part of Approach A prototype for standardized --json-output (Objective #8088).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from erk.tui.data.types import PlanRowData
from erk_shared.gateway.github.metadata.schemas import (
    BRANCH_NAME,
    CREATED_BY,
    CREATED_FROM_SESSION,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    LEARN_PLAN_ISSUE,
    LEARN_PLAN_PR,
    LEARN_RUN_ID,
    LEARN_STATUS,
    OBJECTIVE_ISSUE,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
)
from erk_shared.plan_store.types import Plan


@dataclass(frozen=True)
class PlanListEntry:
    """One row in plan list JSON output.

    All fields are plain data — no Rich markup, no emoji, no click.style.
    """

    plan_id: int
    plan_url: str | None
    title: str
    author: str
    created_at: str

    # PR info
    pr_number: int | None
    pr_url: str | None
    pr_state: str | None
    pr_head_branch: str | None

    # Location
    exists_locally: bool
    worktree_branch: str | None

    # Workflow run
    run_id: str | None
    run_url: str | None
    run_status: str | None
    run_conclusion: str | None

    # Objective
    objective_issue: int | None

    # Comments
    resolved_comment_count: int
    total_comment_count: int


@dataclass(frozen=True)
class PlanListOutput:
    """Full plan list result for JSON output."""

    plans: tuple[PlanListEntry, ...]
    total_count: int


@dataclass(frozen=True)
class PlanViewHeaderFields:
    """Structured header metadata for plan view JSON output."""

    created_by: str | None
    schema_version: str | None
    worktree_name: str | None
    objective_issue: int | None
    source_repo: str | None

    # Local implementation
    last_local_impl_at: str | None
    last_local_impl_event: str | None
    last_local_impl_session: str | None
    last_local_impl_user: str | None

    # Remote
    last_remote_impl_at: str | None
    last_dispatched_at: str | None
    last_dispatched_run_id: str | None

    # Learn
    learn_status: str | None
    learn_plan_issue: int | None
    learn_plan_pr: int | None
    learn_run_url: str | None
    created_from_session: str | None
    last_learn_session: str | None


@dataclass(frozen=True)
class PlanViewOutput:
    """Full plan view result for JSON output."""

    plan_id: str
    title: str
    state: str
    url: str | None
    labels: tuple[str, ...]
    assignees: tuple[str, ...]
    created_at: str
    updated_at: str
    branch_name: str | None
    body: str | None
    header: PlanViewHeaderFields | None


def _format_datetime(value: object) -> str | None:
    """Format a datetime value to ISO 8601 string, or return None."""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, str):
        return value
    return None


def _get_str(info: dict[str, object], key: str) -> str | None:
    """Extract a string value from header info dict."""
    value = info.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return None


def _get_int(info: dict[str, object], key: str) -> int | None:
    """Extract an int value from header info dict."""
    value = info.get(key)
    if isinstance(value, int):
        return value
    return None


def plan_row_to_list_entry(row: PlanRowData) -> PlanListEntry:
    """Convert a PlanRowData to a PlanListEntry for JSON output.

    Maps raw fields from PlanRowData, ignoring display-formatted fields.

    Args:
        row: Plan row data from the data provider

    Returns:
        Clean IR entry with no Rich markup
    """
    return PlanListEntry(
        plan_id=row.plan_id,
        plan_url=row.plan_url,
        title=row.full_title,
        author=row.author,
        created_at=row.created_at.isoformat().replace("+00:00", "Z"),
        pr_number=row.pr_number,
        pr_url=row.pr_url,
        pr_state=row.pr_state,
        pr_head_branch=row.pr_head_branch,
        exists_locally=row.exists_locally,
        worktree_branch=row.worktree_branch,
        run_id=row.run_id,
        run_url=row.run_url,
        run_status=row.run_status,
        run_conclusion=row.run_conclusion,
        objective_issue=row.objective_issue,
        resolved_comment_count=row.resolved_comment_count,
        total_comment_count=row.total_comment_count,
    )


def build_plan_view_output(
    *,
    plan: Plan,
    plan_id: str,
    header_info: dict[str, object],
    include_body: bool,
) -> PlanViewOutput:
    """Build PlanViewOutput from Plan and header metadata.

    Args:
        plan: The Plan domain object
        plan_id: Plan identifier string
        header_info: Dictionary of header fields from plan-header block
        include_body: Whether to include the plan body (--full flag)

    Returns:
        Structured output ready for JSON serialization
    """
    header: PlanViewHeaderFields | None = None
    if header_info:
        header = PlanViewHeaderFields(
            created_by=_get_str(header_info, CREATED_BY),
            schema_version=_get_str(header_info, SCHEMA_VERSION),
            worktree_name=_get_str(header_info, WORKTREE_NAME),
            objective_issue=_get_int(header_info, OBJECTIVE_ISSUE),
            source_repo=_get_str(header_info, SOURCE_REPO),
            last_local_impl_at=_get_str(header_info, LAST_LOCAL_IMPL_AT),
            last_local_impl_event=_get_str(header_info, LAST_LOCAL_IMPL_EVENT),
            last_local_impl_session=_get_str(header_info, LAST_LOCAL_IMPL_SESSION),
            last_local_impl_user=_get_str(header_info, LAST_LOCAL_IMPL_USER),
            last_remote_impl_at=_get_str(header_info, LAST_REMOTE_IMPL_AT),
            last_dispatched_at=_get_str(header_info, LAST_DISPATCHED_AT),
            last_dispatched_run_id=_get_str(header_info, LAST_DISPATCHED_RUN_ID),
            learn_status=_get_str(header_info, LEARN_STATUS),
            learn_plan_issue=_get_int(header_info, LEARN_PLAN_ISSUE),
            learn_plan_pr=_get_int(header_info, LEARN_PLAN_PR),
            learn_run_url=_get_str(header_info, LEARN_RUN_ID),
            created_from_session=_get_str(header_info, CREATED_FROM_SESSION),
            last_learn_session=_get_str(header_info, LAST_LEARN_SESSION),
        )

    branch_name = _get_str(header_info, BRANCH_NAME)

    return PlanViewOutput(
        plan_id=plan_id,
        title=plan.title,
        state=plan.state.value,
        url=plan.url,
        labels=tuple(plan.labels),
        assignees=tuple(plan.assignees),
        created_at=plan.created_at.isoformat().replace("+00:00", "Z"),
        updated_at=plan.updated_at.isoformat().replace("+00:00", "Z"),
        branch_name=branch_name,
        body=plan.body if include_body else None,
        header=header,
    )
