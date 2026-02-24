"""Builder functions for plan output models.

Convert internal data types (PlanRowData, Plan) into output models
for JSON and Rich rendering.
"""

from datetime import datetime

from erk.cli.commands.plan.output_models import (
    PlanListEntry,
    PlanListLearn,
    PlanListObjective,
    PlanListPR,
    PlanListWorkflowRun,
    PlanViewDispatch,
    PlanViewEntry,
    PlanViewHeader,
    PlanViewImplementation,
    PlanViewLearn,
)
from erk.core.display_utils import strip_rich_markup
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
from erk_shared.gateway.github.parsing import (
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.plan_store.types import Plan


def _format_datetime(dt: datetime) -> str:
    """Format a datetime as ISO 8601 string."""
    return dt.isoformat().replace("+00:00", "Z")


def _safe_str(value: object) -> str | None:
    """Convert value to string, returning None if value is None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _format_datetime(value)
    return str(value)


def _safe_int(value: object) -> int | None:
    """Convert value to int, returning None if value is not an int."""
    if isinstance(value, int):
        return value
    return None


def build_plan_list_entry(row: PlanRowData) -> PlanListEntry:
    """Build a PlanListEntry from a PlanRowData.

    Args:
        row: TUI plan row data

    Returns:
        PlanListEntry output model suitable for JSON/table rendering
    """
    # Build nested PR
    pr: PlanListPR | None = None
    if row.pr_number is not None:
        pr = PlanListPR(
            number=row.pr_number,
            url=row.pr_url,
            state=row.pr_state,
            title=row.pr_title,
            head_branch=row.pr_head_branch,
            resolved_comments=row.resolved_comment_count,
            total_comments=row.total_comment_count,
        )

    # Build nested workflow run
    workflow_run: PlanListWorkflowRun | None = None
    if row.run_id is not None:
        workflow_run = PlanListWorkflowRun(
            run_id=row.run_id,
            status=row.run_status,
            conclusion=row.run_conclusion,
            url=row.run_url,
        )

    # Build nested learn
    learn = PlanListLearn(
        status=row.learn_status,
        plan_issue=row.learn_plan_issue,
        plan_pr=row.learn_plan_pr,
        run_url=row.learn_run_url,
    )

    # Build nested objective
    objective: PlanListObjective | None = None
    if row.objective_issue is not None:
        objective = PlanListObjective(
            issue=row.objective_issue,
            url=row.objective_url,
            done_nodes=row.objective_done_nodes,
            total_nodes=row.objective_total_nodes,
        )

    # Determine branch: prefer pr_head_branch, fall back to worktree_branch
    branch = row.pr_head_branch or row.worktree_branch

    return PlanListEntry(
        plan_id=row.plan_id,
        plan_url=row.plan_url,
        title=row.full_title,
        lifecycle_stage=strip_rich_markup(row.lifecycle_display),
        status_display=row.status_display,
        created_at=_format_datetime(row.created_at),
        updated_at=_format_datetime(row.updated_at),
        author=row.author,
        branch=branch,
        exists_locally=row.exists_locally,
        has_cloud_run=row.run_url is not None,
        pr=pr,
        workflow_run=workflow_run,
        learn=learn,
        objective=objective,
        checks_display=strip_rich_markup(row.checks_display),
        comments_display=strip_rich_markup(row.comments_display),
    )


def build_plan_view_entry(
    plan: Plan,
    *,
    header_info: dict[str, object],
    include_body: bool,
) -> PlanViewEntry:
    """Build a PlanViewEntry from a Plan and header metadata.

    Args:
        plan: Plan from plan store
        header_info: Parsed plan-header metadata fields
        include_body: Whether to include the plan body text

    Returns:
        PlanViewEntry output model suitable for JSON/detail rendering
    """
    # Build nested header
    header = PlanViewHeader(
        created_by=_safe_str(header_info.get(CREATED_BY)),
        schema_version=_safe_str(header_info.get(SCHEMA_VERSION)),
        worktree=_safe_str(header_info.get(WORKTREE_NAME)),
        objective_issue=_safe_int(header_info.get(OBJECTIVE_ISSUE)),
        source_repo=_safe_str(header_info.get(SOURCE_REPO)),
    )

    # Build nested implementation
    implementation = PlanViewImplementation(
        last_local_impl_at=_safe_str(header_info.get(LAST_LOCAL_IMPL_AT)),
        last_local_impl_event=_safe_str(header_info.get(LAST_LOCAL_IMPL_EVENT)),
        last_local_impl_session=_safe_str(header_info.get(LAST_LOCAL_IMPL_SESSION)),
        last_local_impl_user=_safe_str(header_info.get(LAST_LOCAL_IMPL_USER)),
        last_remote_impl_at=_safe_str(header_info.get(LAST_REMOTE_IMPL_AT)),
    )

    # Build nested dispatch
    dispatch = PlanViewDispatch(
        last_dispatched_at=_safe_str(header_info.get(LAST_DISPATCHED_AT)),
        last_dispatched_run_id=_safe_str(header_info.get(LAST_DISPATCHED_RUN_ID)),
    )

    # Build nested learn
    learn_status_raw = _safe_str(header_info.get(LEARN_STATUS))
    learn_plan_issue = _safe_int(header_info.get(LEARN_PLAN_ISSUE))
    learn_plan_pr = _safe_int(header_info.get(LEARN_PLAN_PR))

    # Resolve workflow URL for learn section
    workflow_url: str | None = None
    if learn_status_raw == "pending":
        learn_run_id_raw = header_info.get(LEARN_RUN_ID)
        if learn_run_id_raw is not None and plan.url is not None:
            owner_repo = extract_owner_repo_from_github_url(plan.url)
            if owner_repo is not None:
                workflow_url = construct_workflow_run_url(
                    owner_repo[0], owner_repo[1], str(learn_run_id_raw)
                )

    learn = PlanViewLearn(
        status=learn_status_raw,
        plan_issue=learn_plan_issue,
        plan_pr=learn_plan_pr,
        workflow_url=workflow_url,
        created_from_session=_safe_str(header_info.get(CREATED_FROM_SESSION)),
        last_learn_session=_safe_str(header_info.get(LAST_LEARN_SESSION)),
    )

    # Branch from header
    branch = _safe_str(header_info.get(BRANCH_NAME))

    return PlanViewEntry(
        plan_id=int(plan.plan_identifier),
        title=plan.title,
        state=plan.state.value,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        updated_at=plan.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        branch=branch,
        body=plan.body if include_body else None,
        header=header,
        implementation=implementation,
        dispatch=dispatch,
        learn=learn,
    )
