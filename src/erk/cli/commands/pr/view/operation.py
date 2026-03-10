"""Core operation for pr view (transport-independent).

Contains the request type and operation function that both the
human command (pr/view/cli.py) and machine command (pr/view/json_cli.py) share.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.plan_store.conversion import github_issue_to_plan
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class PrViewRequest:
    """Request type for pr view."""

    identifier: str | None = None
    full: bool = False


@dataclass(frozen=True)
class PrViewResult:
    """JSON result for erk pr view."""

    plan_id: str
    title: str
    state: str
    url: str | None
    labels: list[str]
    assignees: list[str]
    created_at: str
    updated_at: str
    objective_id: int | None
    branch: str | None
    header_fields: dict[str, object]
    body: str | None

    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "plan_id": self.plan_id,
            "title": self.title,
            "state": self.state,
            "url": self.url,
            "labels": self.labels,
            "assignees": self.assignees,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "objective_id": self.objective_id,
            "branch": self.branch,
            "header_fields": _serialize_header_fields(self.header_fields),
        }
        if self.body is not None:
            result["body"] = self.body
        return result


def _serialize_header_fields(fields: dict[str, object]) -> dict[str, object]:
    """Serialize header fields, converting datetime values to ISO 8601 strings."""
    result: dict[str, object] = {}
    for key, value in fields.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def run_pr_view(
    ctx: ErkContext,
    request: PrViewRequest,
    *,
    repo_id: GitHubRepoId,
) -> PrViewResult | MachineCommandError:
    """Execute pr view operation.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        repo_id: Resolved GitHub repo ID

    Returns:
        PrViewResult or MachineCommandError
    """
    repo_root = None if isinstance(ctx.repo, NoRepoSentinel) else ctx.repo.root
    plan_id: str | None = None
    identifier = request.identifier

    # If no identifier, infer from branch (local only)
    if identifier is None:
        if isinstance(ctx.repo, NoRepoSentinel):
            return MachineCommandError(
                error_type="missing_identifier",
                message=(
                    "A plan identifier is required in remote mode (cannot infer from branch).\n"
                    "Usage: provide identifier in request JSON"
                ),
            )

        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            return MachineCommandError(
                error_type="missing_identifier",
                message="No identifier specified and could not infer from branch name",
            )

        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.repo.root, branch)
        if plan_id is None:
            return MachineCommandError(
                error_type="missing_identifier",
                message="No identifier specified and could not infer from branch name",
            )

        identifier = plan_id

    plan_number = parse_issue_identifier(identifier)
    if plan_id is None:
        plan_id = str(plan_number)

    remote = get_remote_github(ctx)

    issue = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=plan_number)
    if isinstance(issue, IssueNotFound):
        return MachineCommandError(
            error_type="not_found",
            message=f"Plan #{plan_id} not found",
        )

    plan = github_issue_to_plan(issue)

    # Optional local enrichment for richer header metadata
    if repo_root is not None:
        all_meta = ctx.plan_backend.get_all_metadata_fields(repo_root, plan_id)
        if isinstance(all_meta, PlanNotFound):
            header_info: dict[str, object] = plan.header_fields
        else:
            header_info = all_meta
    else:
        header_info = plan.header_fields

    return PrViewResult(
        plan_id=plan_id,
        title=plan.title,
        state=plan.state.value,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
        objective_id=plan.objective_id,
        branch=str(header_info[BRANCH_NAME]) if BRANCH_NAME in header_info else None,
        header_fields=header_info,
        body=plan.body if request.full else None,
    )
