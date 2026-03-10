"""Core request/result contract for `erk pr view`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.gateway.github.parsing import parse_plan_number_from_url
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub
from erk_shared.plan_store.conversion import github_issue_to_plan
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class PrViewRequest:
    """Canonical request for viewing a plan."""

    identifier: str | None = None
    full: bool = False
    repo: str | None = None


@dataclass(frozen=True)
class PrViewResult:
    """Canonical result for viewing a plan."""

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


def run_pr_view(
    request: PrViewRequest,
    *,
    ctx: ErkContext,
) -> PrViewResult | MachineCommandError:
    """Fetch a plan for human or machine adapters."""

    repo_id_result = _resolve_repo_id(ctx, repo=request.repo)
    if isinstance(repo_id_result, MachineCommandError):
        return repo_id_result

    plan_id = request.identifier
    repo_root = None if isinstance(ctx.repo, NoRepoSentinel) else ctx.repo.root
    if plan_id is None:
        if isinstance(ctx.repo, NoRepoSentinel):
            return MachineCommandError(
                error_type="cli_error",
                message=(
                    "A plan identifier is required in remote mode (cannot infer from branch).\n"
                    "Usage: erk pr view <number> --repo owner/repo"
                ),
            )

        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            return MachineCommandError(
                error_type="cli_error",
                message=(
                    "No identifier specified and could not infer from branch name\n"
                    "Usage: erk pr view <identifier>\n"
                    "Or run from a plan branch with a plan reference file"
                ),
            )

        resolved_plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.repo.root, branch)
        if resolved_plan_id is None:
            return MachineCommandError(
                error_type="cli_error",
                message=(
                    "No identifier specified and could not infer from branch name\n"
                    "Usage: erk pr view <identifier>\n"
                    "Or run from a plan branch with a plan reference file"
                ),
            )
        plan_id = resolved_plan_id

    plan_number_result = _parse_plan_identifier(plan_id)
    if isinstance(plan_number_result, MachineCommandError):
        return plan_number_result

    remote = _resolve_remote_github(ctx)
    if isinstance(remote, MachineCommandError):
        return remote

    issue = remote.get_issue(
        owner=repo_id_result.owner,
        repo=repo_id_result.repo,
        number=plan_number_result,
    )
    if isinstance(issue, IssueNotFound):
        return MachineCommandError(
            error_type="plan_not_found",
            message=f"Plan #{plan_id} not found",
        )

    plan = github_issue_to_plan(issue)

    if repo_root is not None:
        all_meta = ctx.plan_backend.get_all_metadata_fields(repo_root, str(plan_number_result))
        if isinstance(all_meta, PlanNotFound):
            header_info = plan.header_fields
        else:
            header_info = all_meta
    else:
        header_info = plan.header_fields

    branch = None
    if BRANCH_NAME in header_info:
        branch = str(header_info[BRANCH_NAME])

    return PrViewResult(
        plan_id=str(plan_number_result),
        title=plan.title,
        state=plan.state.value,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
        objective_id=plan.objective_id,
        branch=branch,
        header_fields=header_info,
        body=plan.body if request.full else None,
    )


def _serialize_header_fields(fields: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in fields.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def _parse_plan_identifier(identifier: str) -> int | MachineCommandError:
    if identifier.upper().startswith("P") and identifier[1:].isdigit():
        return int(identifier[1:])

    if identifier.isdigit():
        return int(identifier)

    issue_number = parse_plan_number_from_url(identifier)
    if issue_number is not None:
        return issue_number

    return MachineCommandError(
        error_type="cli_error",
        message=(
            f"Invalid plan number or URL: {identifier}\n\n"
            "Expected formats:\n"
            "  • Plain number: 123\n"
            "  • P-prefixed: P123\n"
            "  • GitHub URL: https://github.com/owner/repo/issues/456"
        ),
    )


def _resolve_repo_id(
    ctx: ErkContext,
    *,
    repo: str | None,
) -> GitHubRepoId | MachineCommandError:
    if repo is not None:
        if "/" not in repo or repo.count("/") != 1:
            return MachineCommandError(
                error_type="cli_error",
                message=(
                    f"Invalid --repo format: '{repo}'\n"
                    "Expected format: owner/repo (e.g., dagster-io/erk)"
                ),
            )
        owner, repo_name = repo.split("/")
        return GitHubRepoId(owner=owner, repo=repo_name)

    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        return MachineCommandError(
            error_type="cli_error",
            message=(
                "Cannot determine target repository.\n"
                "Use --repo owner/repo or run from inside a git repository."
            ),
        )

    return GitHubRepoId(owner=ctx.repo.github.owner, repo=ctx.repo.github.repo)


def _resolve_remote_github(ctx: ErkContext) -> RemoteGitHub | MachineCommandError:
    if ctx.remote_github is not None:
        return ctx.remote_github

    if ctx.http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication required.\nRun 'gh auth login' to authenticate.",
        )

    return RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)
