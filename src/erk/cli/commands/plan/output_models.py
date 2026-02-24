"""Output models for plan commands.

Frozen dataclasses with Meta inner classes that declare rendering metadata.
A generic renderer inspects Meta to produce Rich tables, detail views, or JSON.
"""

from dataclasses import dataclass

from erk.cli.output_framework.rendering_types import (
    Column,
    DetailField,
    DetailMeta,
    DetailSection,
    TableMeta,
)

# -- Nested types for PlanListEntry --


@dataclass(frozen=True)
class PlanListPR:
    """PR info nested within a plan list entry."""

    number: int
    url: str | None
    state: str | None
    title: str | None
    head_branch: str | None
    resolved_comments: int
    total_comments: int


@dataclass(frozen=True)
class PlanListWorkflowRun:
    """Workflow run info nested within a plan list entry."""

    run_id: str
    status: str | None
    conclusion: str | None
    url: str | None


@dataclass(frozen=True)
class PlanListLearn:
    """Learn status nested within a plan list entry."""

    status: str | None
    plan_issue: int | None
    plan_pr: int | None
    run_url: str | None


@dataclass(frozen=True)
class PlanListObjective:
    """Objective info nested within a plan list entry."""

    issue: int
    url: str | None
    done_nodes: int
    total_nodes: int


# -- Main list entry --


@dataclass(frozen=True)
class PlanListEntry:
    """Output model for a single row in the plan list table.

    The Meta inner class declares all table columns and the JSON root key.
    Format methods on this class handle custom cell rendering.
    """

    plan_id: int
    plan_url: str | None
    title: str
    lifecycle_stage: str
    status_display: str
    created_at: str
    updated_at: str
    author: str
    branch: str | None
    exists_locally: bool
    has_cloud_run: bool
    pr: PlanListPR | None
    workflow_run: PlanListWorkflowRun | None
    learn: PlanListLearn
    objective: PlanListObjective | None
    checks_display: str
    comments_display: str

    class Meta:
        table = TableMeta(
            json_root="plans",
            columns=(
                Column(
                    field="plan_id",
                    header="pr",
                    width=6,
                    style="cyan",
                    no_wrap=True,
                    format_method="format_plan_id",
                    link_field="plan_url",
                ),
                Column(
                    field="lifecycle_stage",
                    header="stage",
                    width=8,
                    style=None,
                    no_wrap=True,
                    format_method=None,
                    link_field=None,
                ),
                Column(
                    field="status_display",
                    header="sts",
                    width=4,
                    style=None,
                    no_wrap=True,
                    format_method=None,
                    link_field=None,
                ),
                Column(
                    field="created_at",
                    header="created",
                    width=7,
                    style=None,
                    no_wrap=True,
                    format_method="format_created",
                    link_field=None,
                ),
                Column(
                    field="objective",
                    header="obj",
                    width=5,
                    style=None,
                    no_wrap=True,
                    format_method="format_objective",
                    link_field=None,
                ),
                Column(
                    field="exists_locally",
                    header="loc",
                    width=3,
                    style=None,
                    no_wrap=True,
                    format_method="format_location",
                    link_field=None,
                ),
                Column(
                    field="branch",
                    header="branch",
                    width=42,
                    style=None,
                    no_wrap=True,
                    format_method="format_branch",
                    link_field=None,
                ),
                Column(
                    field="workflow_run",
                    header="run-id",
                    width=10,
                    style=None,
                    no_wrap=True,
                    format_method="format_run_id",
                    link_field=None,
                ),
                Column(
                    field="workflow_run",
                    header="run",
                    width=3,
                    style=None,
                    no_wrap=True,
                    format_method="format_run_state",
                    link_field=None,
                ),
                Column(
                    field="author",
                    header="author",
                    width=9,
                    style=None,
                    no_wrap=True,
                    format_method=None,
                    link_field=None,
                ),
                Column(
                    field="checks_display",
                    header="chks",
                    width=8,
                    style=None,
                    no_wrap=True,
                    format_method=None,
                    link_field=None,
                ),
                Column(
                    field="comments_display",
                    header="cmts",
                    width=5,
                    style=None,
                    no_wrap=True,
                    format_method=None,
                    link_field=None,
                ),
            ),
        )

    def format_plan_id(self) -> str:
        return f"#{self.plan_id}"

    def format_created(self) -> str:
        return self.created_at

    def format_objective(self) -> str:
        if self.objective is None:
            return "-"
        return f"#{self.objective.issue}"

    def format_location(self) -> str:
        parts: list[str] = []
        if self.exists_locally:
            parts.append("\U0001f4bb")
        if self.has_cloud_run:
            parts.append("\u2601")
        return "".join(parts) if parts else "-"

    def format_branch(self) -> str:
        return self.branch or "-"

    def format_run_id(self) -> str:
        if self.workflow_run is None:
            return "-"
        return self.workflow_run.run_id

    def format_run_state(self) -> str:
        if self.workflow_run is None:
            return "-"
        status = self.workflow_run.status
        conclusion = self.workflow_run.conclusion
        if status == "completed":
            if conclusion == "success":
                return "\u2705"
            if conclusion == "failure":
                return "\u274c"
            if conclusion == "cancelled":
                return "\u26d4"
            return "\u2753"
        if status == "in_progress":
            return "\u27f3"
        if status == "queued":
            return "\u29d7"
        return "\u2753"

    def format_comments(self) -> str:
        return self.comments_display


# -- Nested types for PlanViewEntry --


@dataclass(frozen=True)
class PlanViewHeader:
    """Header metadata for plan detail view."""

    created_by: str | None
    schema_version: str | None
    worktree: str | None
    objective_issue: int | None
    source_repo: str | None


@dataclass(frozen=True)
class PlanViewImplementation:
    """Implementation info for plan detail view."""

    last_local_impl_at: str | None
    last_local_impl_event: str | None
    last_local_impl_session: str | None
    last_local_impl_user: str | None
    last_remote_impl_at: str | None


@dataclass(frozen=True)
class PlanViewDispatch:
    """Remote dispatch info for plan detail view."""

    last_dispatched_at: str | None
    last_dispatched_run_id: str | None


@dataclass(frozen=True)
class PlanViewLearn:
    """Learn status for plan detail view."""

    status: str | None
    plan_issue: int | None
    plan_pr: int | None
    workflow_url: str | None
    created_from_session: str | None
    last_learn_session: str | None


# -- Main detail entry --


@dataclass(frozen=True)
class PlanViewEntry:
    """Output model for the plan view detail display.

    The Meta inner class declares all sections and fields for detail rendering.
    Format methods handle custom field formatting.
    """

    plan_id: int
    title: str
    state: str
    url: str | None
    labels: list[str]
    assignees: list[str]
    created_at: str
    updated_at: str
    branch: str | None
    body: str | None
    header: PlanViewHeader
    implementation: PlanViewImplementation
    dispatch: PlanViewDispatch
    learn: PlanViewLearn

    class Meta:
        detail = DetailMeta(
            json_root="plan",
            sections=(
                DetailSection(
                    title=None,
                    fields=(
                        DetailField(
                            field="title",
                            label="Title",
                            format_method=None,
                            style="bold",
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="state",
                            label="State",
                            format_method="format_state",
                            style=None,
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="plan_id",
                            label="ID",
                            format_method="format_id",
                            style=None,
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="url",
                            label="URL",
                            format_method="format_url",
                            style=None,
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="branch",
                            label="Branch",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="labels",
                            label="Labels",
                            format_method="format_labels",
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="assignees",
                            label="Assignees",
                            format_method="format_assignees",
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="created_at",
                            label="Created",
                            format_method=None,
                            style=None,
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="updated_at",
                            label="Updated",
                            format_method=None,
                            style=None,
                            skip_if_none=False,
                        ),
                    ),
                    skip_if_empty=False,
                ),
                DetailSection(
                    title="Header",
                    fields=(
                        DetailField(
                            field="header.created_by",
                            label="Created by",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="header.schema_version",
                            label="Schema version",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="header.worktree",
                            label="Worktree",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="header.objective_issue",
                            label="Objective",
                            format_method="format_objective",
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="header.source_repo",
                            label="Source repo",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                    ),
                    skip_if_empty=True,
                ),
                DetailSection(
                    title="Local Implementation",
                    fields=(
                        DetailField(
                            field="implementation.last_local_impl_at",
                            label="Last impl",
                            format_method="format_local_impl",
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="implementation.last_local_impl_session",
                            label="Session",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="implementation.last_local_impl_user",
                            label="User",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                    ),
                    skip_if_empty=True,
                ),
                DetailSection(
                    title="Remote Implementation",
                    fields=(
                        DetailField(
                            field="implementation.last_remote_impl_at",
                            label="Last impl",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                    ),
                    skip_if_empty=True,
                ),
                DetailSection(
                    title="Remote Dispatch",
                    fields=(
                        DetailField(
                            field="dispatch.last_dispatched_at",
                            label="Last dispatched",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="dispatch.last_dispatched_run_id",
                            label="Run ID",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                    ),
                    skip_if_empty=True,
                ),
                DetailSection(
                    title="Learn",
                    fields=(
                        DetailField(
                            field="learn.status",
                            label="Status",
                            format_method="format_learn_status",
                            style=None,
                            skip_if_none=False,
                        ),
                        DetailField(
                            field="learn.workflow_url",
                            label="Workflow",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="learn.created_from_session",
                            label="Plan session",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                        DetailField(
                            field="learn.last_learn_session",
                            label="Learn session",
                            format_method=None,
                            style=None,
                            skip_if_none=True,
                        ),
                    ),
                    skip_if_empty=False,
                ),
            ),
        )

    def format_state(self) -> str:
        return self.state

    def format_id(self) -> str:
        return f"#{self.plan_id}"

    def format_url(self) -> str:
        return self.url or "-"

    def format_labels(self) -> str | None:
        if not self.labels:
            return None
        return ", ".join(f"[{label}]" for label in self.labels)

    def format_assignees(self) -> str | None:
        if not self.assignees:
            return None
        return ", ".join(self.assignees)

    def format_objective(self) -> str | None:
        if self.header.objective_issue is None:
            return None
        return f"#{self.header.objective_issue}"

    def format_local_impl(self) -> str | None:
        if self.implementation.last_local_impl_at is None:
            return None
        event = self.implementation.last_local_impl_event
        event_str = f" ({event})" if event else ""
        return f"{self.implementation.last_local_impl_at}{event_str}"

    def format_learn_status(self) -> str:
        status = self.learn.status
        if status is None or status == "not_started":
            return "- not started"
        if status == "pending":
            return "in progress"
        if status == "completed_no_plan":
            return "no insights"
        if status == "completed_with_plan" and self.learn.plan_issue is not None:
            return f"#{self.learn.plan_issue}"
        if status == "pending_review" and self.learn.plan_pr is not None:
            return f"draft PR #{self.learn.plan_pr}"
        if status == "plan_completed" and self.learn.plan_pr is not None:
            return f"completed #{self.learn.plan_pr}"
        return "- not started"
