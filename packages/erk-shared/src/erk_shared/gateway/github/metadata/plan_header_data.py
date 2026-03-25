"""Typed frozen dataclass for plan-header metadata."""

from dataclasses import dataclass
from typing import Any

from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    find_metadata_block,
    render_metadata_block,
)
from erk_shared.gateway.github.metadata.schemas import (
    BRANCH_NAME,
    CI_SUMMARY_COMMENT_ID,
    CREATED_AT,
    CREATED_BY,
    CREATED_FROM_SESSION,
    CREATED_FROM_WORKFLOW_RUN_URL,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_NODE_ID,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_AT,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    LAST_REMOTE_IMPL_RUN_ID,
    LAST_REMOTE_IMPL_SESSION_ID,
    LAST_SESSION_AT,
    LAST_SESSION_BRANCH,
    LAST_SESSION_ID,
    LAST_SESSION_SOURCE,
    LEARN_MATERIALS_BRANCH,
    LEARN_PLAN_ISSUE,
    LEARN_PLAN_PR,
    LEARN_RUN_ID,
    LEARN_STATUS,
    LEARNED_FROM_ISSUE,
    LIFECYCLE_STAGE,
    NODE_IDS,
    OBJECTIVE_ISSUE,
    PLAN_COMMENT_ID,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
    LearnStatusValue,
    PlanHeaderSchema,
    SessionSourceValue,
)
from erk_shared.gateway.github.metadata.types import BlockKeys, MetadataBlock


@dataclass(frozen=True)
class PlanHeaderData:
    """Typed representation of plan-header metadata.

    Parse-once, access-many: construct via ``from_dict`` or ``from_issue_body``,
    then access typed fields directly. Use ``dataclasses.replace()`` for updates.

    ``schema_version`` is NOT a field -- always ``"2"``, injected by ``to_dict()``.
    ``node_ids`` uses ``tuple[str, ...]`` (frozen-dataclass convention);
    converted to/from ``list`` at serialization boundaries.
    """

    # Required
    created_at: str
    created_by: str

    # Optional (32 fields, all default None)
    worktree_name: str | None = None
    branch_name: str | None = None
    plan_comment_id: int | None = None
    ci_summary_comment_id: int | None = None
    last_dispatched_run_id: str | None = None
    last_dispatched_node_id: str | None = None
    last_dispatched_at: str | None = None
    last_local_impl_at: str | None = None
    last_local_impl_event: str | None = None
    last_local_impl_session: str | None = None
    last_local_impl_user: str | None = None
    last_remote_impl_at: str | None = None
    last_remote_impl_run_id: str | None = None
    last_remote_impl_session_id: str | None = None
    source_repo: str | None = None
    objective_issue: int | None = None
    node_ids: tuple[str, ...] | None = None
    created_from_session: str | None = None
    created_from_workflow_run_url: str | None = None
    last_learn_session: str | None = None
    last_learn_at: str | None = None
    learn_status: LearnStatusValue | None = None
    learn_run_id: str | None = None
    last_session_branch: str | None = None
    last_session_id: str | None = None
    last_session_at: str | None = None
    last_session_source: SessionSourceValue | None = None
    learn_plan_issue: int | None = None
    learn_plan_pr: int | None = None
    learned_from_issue: int | None = None
    learn_materials_branch: str | None = None
    lifecycle_stage: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanHeaderData":
        """Construct from a parsed YAML dict.

        Handles ``node_ids`` list-to-tuple conversion.
        Ignores ``schema_version`` (always injected by ``to_dict``).
        """
        raw_node_ids = data.get(NODE_IDS)
        node_ids: tuple[str, ...] | None = None
        if isinstance(raw_node_ids, list):
            node_ids = tuple(raw_node_ids)

        return cls(
            created_at=data[CREATED_AT],
            created_by=data[CREATED_BY],
            worktree_name=data.get(WORKTREE_NAME),
            branch_name=data.get(BRANCH_NAME),
            plan_comment_id=data.get(PLAN_COMMENT_ID),
            ci_summary_comment_id=data.get(CI_SUMMARY_COMMENT_ID),
            last_dispatched_run_id=data.get(LAST_DISPATCHED_RUN_ID),
            last_dispatched_node_id=data.get(LAST_DISPATCHED_NODE_ID),
            last_dispatched_at=data.get(LAST_DISPATCHED_AT),
            last_local_impl_at=data.get(LAST_LOCAL_IMPL_AT),
            last_local_impl_event=data.get(LAST_LOCAL_IMPL_EVENT),
            last_local_impl_session=data.get(LAST_LOCAL_IMPL_SESSION),
            last_local_impl_user=data.get(LAST_LOCAL_IMPL_USER),
            last_remote_impl_at=data.get(LAST_REMOTE_IMPL_AT),
            last_remote_impl_run_id=data.get(LAST_REMOTE_IMPL_RUN_ID),
            last_remote_impl_session_id=data.get(LAST_REMOTE_IMPL_SESSION_ID),
            source_repo=data.get(SOURCE_REPO),
            objective_issue=data.get(OBJECTIVE_ISSUE),
            node_ids=node_ids,
            created_from_session=data.get(CREATED_FROM_SESSION),
            created_from_workflow_run_url=data.get(CREATED_FROM_WORKFLOW_RUN_URL),
            last_learn_session=data.get(LAST_LEARN_SESSION),
            last_learn_at=data.get(LAST_LEARN_AT),
            learn_status=data.get(LEARN_STATUS),
            learn_run_id=data.get(LEARN_RUN_ID),
            last_session_branch=data.get(LAST_SESSION_BRANCH),
            last_session_id=data.get(LAST_SESSION_ID),
            last_session_at=data.get(LAST_SESSION_AT),
            last_session_source=data.get(LAST_SESSION_SOURCE),
            learn_plan_issue=data.get(LEARN_PLAN_ISSUE),
            learn_plan_pr=data.get(LEARN_PLAN_PR),
            learned_from_issue=data.get(LEARNED_FROM_ISSUE),
            learn_materials_branch=data.get(LEARN_MATERIALS_BRANCH),
            lifecycle_stage=data.get(LIFECYCLE_STAGE),
        )

    @classmethod
    def from_issue_body(cls, issue_body: str) -> "PlanHeaderData | None":
        """Parse a plan-header block from an issue body.

        Calls ``find_metadata_block`` once, then delegates to ``from_dict``.

        Returns:
            ``PlanHeaderData`` if found, ``None`` otherwise.
        """
        block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
        if block is None:
            return None
        return cls.from_dict(block.data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for YAML rendering.

        Injects ``schema_version: "2"``. Converts ``node_ids`` tuple to list.
        Only includes optional fields when non-None.
        """
        data: dict[str, Any] = {
            SCHEMA_VERSION: "2",
            CREATED_AT: self.created_at,
            CREATED_BY: self.created_by,
        }

        _OPTIONAL_FIELDS: tuple[tuple[str, Any], ...] = (
            (WORKTREE_NAME, self.worktree_name),
            (BRANCH_NAME, self.branch_name),
            (PLAN_COMMENT_ID, self.plan_comment_id),
            (CI_SUMMARY_COMMENT_ID, self.ci_summary_comment_id),
            (LAST_DISPATCHED_RUN_ID, self.last_dispatched_run_id),
            (LAST_DISPATCHED_NODE_ID, self.last_dispatched_node_id),
            (LAST_DISPATCHED_AT, self.last_dispatched_at),
            (LAST_LOCAL_IMPL_AT, self.last_local_impl_at),
            (LAST_LOCAL_IMPL_EVENT, self.last_local_impl_event),
            (LAST_LOCAL_IMPL_SESSION, self.last_local_impl_session),
            (LAST_LOCAL_IMPL_USER, self.last_local_impl_user),
            (LAST_REMOTE_IMPL_AT, self.last_remote_impl_at),
            (LAST_REMOTE_IMPL_RUN_ID, self.last_remote_impl_run_id),
            (LAST_REMOTE_IMPL_SESSION_ID, self.last_remote_impl_session_id),
            (SOURCE_REPO, self.source_repo),
            (OBJECTIVE_ISSUE, self.objective_issue),
            (NODE_IDS, list(self.node_ids) if self.node_ids is not None else None),
            (CREATED_FROM_SESSION, self.created_from_session),
            (CREATED_FROM_WORKFLOW_RUN_URL, self.created_from_workflow_run_url),
            (LAST_LEARN_SESSION, self.last_learn_session),
            (LAST_LEARN_AT, self.last_learn_at),
            (LEARN_STATUS, self.learn_status),
            (LEARN_RUN_ID, self.learn_run_id),
            (LAST_SESSION_BRANCH, self.last_session_branch),
            (LAST_SESSION_ID, self.last_session_id),
            (LAST_SESSION_AT, self.last_session_at),
            (LAST_SESSION_SOURCE, self.last_session_source),
            (LEARN_PLAN_ISSUE, self.learn_plan_issue),
            (LEARN_PLAN_PR, self.learn_plan_pr),
            (LEARNED_FROM_ISSUE, self.learned_from_issue),
            (LEARN_MATERIALS_BRANCH, self.learn_materials_branch),
            (LIFECYCLE_STAGE, self.lifecycle_stage),
        )

        for key, value in _OPTIONAL_FIELDS:
            if value is not None:
                data[key] = value

        return data

    def to_metadata_block(self) -> MetadataBlock:
        """Serialize, validate via ``PlanHeaderSchema``, return ``MetadataBlock``."""
        data = self.to_dict()
        schema = PlanHeaderSchema()
        return create_metadata_block(
            key=schema.get_key(),
            data=data,
            schema=schema,
        )

    def to_rendered_block(self) -> str:
        """Serialize, validate, and render as markdown."""
        return render_metadata_block(self.to_metadata_block())
