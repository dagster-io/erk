"""Core operations for workflow run machine commands."""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.cli.ensure import UserFacingCliError
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.github.types import WorkflowRun
from erk_shared.subprocess_utils import run_subprocess_with_context


def _serialize_workflow_run(
    workflow_run: WorkflowRun,
    *,
    owner: str,
    repo: str,
) -> dict[str, Any]:
    workflow_name = _workflow_name_for_run(workflow_run)
    return {
        "run_id": workflow_run.run_id,
        "node_id": workflow_run.node_id,
        "status": workflow_run.status,
        "conclusion": workflow_run.conclusion,
        "branch": _safe_value(lambda: workflow_run.branch),
        "head_sha": workflow_run.head_sha,
        "display_title": _safe_value(lambda: workflow_run.display_title),
        "created_at": _serialize_datetime(workflow_run.created_at),
        "workflow": workflow_name,
        "workflow_path": workflow_run.workflow_path,
        "url": _build_workflow_run_url(owner=owner, repo=repo, run_id=workflow_run.run_id),
    }


def _serialize_datetime(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None
    return timestamp.isoformat()


def _safe_value(read_value: Any) -> Any:
    try:
        return read_value()
    except AttributeError:
        return None


def _workflow_name_for_run(workflow_run: WorkflowRun) -> str | None:
    workflow_path = workflow_run.workflow_path
    if workflow_path is None:
        return None

    workflow_file = Path(workflow_path).name
    for workflow_name, mapped_file in WORKFLOW_COMMAND_MAP.items():
        if mapped_file == workflow_file:
            return workflow_name

    return workflow_file


def _build_workflow_run_url(*, owner: str, repo: str, run_id: str) -> str:
    return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"


def _resolve_repo_target(
    ctx: ErkContext,
    *,
    target_repo: str | None,
) -> tuple[str, str] | MachineCommandError:
    try:
        return resolve_owner_repo(ctx, target_repo=target_repo)
    except UserFacingCliError as error:
        return MachineCommandError(
            error_type=str(error.error_type),
            message=error.format_message(),
        )


def _get_local_repo_root(ctx: ErkContext) -> Path | None:
    if isinstance(ctx.repo, NoRepoSentinel):
        return None
    return ctx.repo.root


def _parse_created_at(created_at_str: str | None) -> datetime | None:
    if created_at_str is None or created_at_str == "":
        return None
    return datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))


def _workflow_run_from_api_data(data: dict[str, Any]) -> WorkflowRun:
    return WorkflowRun(
        run_id=str(data["id"]),
        node_id=data.get("node_id"),
        status=data["status"],
        conclusion=data.get("conclusion"),
        branch=data["head_branch"],
        head_sha=data["head_sha"],
        display_title=data.get("display_title"),
        created_at=_parse_created_at(data.get("created_at")),
        workflow_path=data.get("path"),
    )


def _list_workflow_runs_remote(
    ctx: ErkContext,
    *,
    owner: str,
    repo: str,
    limit: int,
    actor: str | None,
) -> list[WorkflowRun] | MachineCommandError:
    if ctx.http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication not available",
        )

    endpoint = f"repos/{owner}/{repo}/actions/runs?per_page={limit}"
    if actor is not None:
        endpoint = f"{endpoint}&actor={actor}"

    response = ctx.http_client.get(endpoint)
    runs_data = response.get("workflow_runs", [])
    return [_workflow_run_from_api_data(run_data) for run_data in runs_data]


def _get_workflow_run_remote(
    ctx: ErkContext,
    *,
    owner: str,
    repo: str,
    run_id: str,
) -> WorkflowRun | MachineCommandError:
    if ctx.http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication not available",
        )

    try:
        response = ctx.http_client.get(f"repos/{owner}/{repo}/actions/runs/{run_id}")
    except HttpError:
        return MachineCommandError(
            error_type="not_found",
            message=f"Workflow run {run_id} not found",
        )

    return _workflow_run_from_api_data(response)


def _get_run_logs_remote(
    *,
    owner: str,
    repo: str,
    run_id: str,
) -> str | MachineCommandError:
    try:
        result = run_subprocess_with_context(
            cmd=["gh", "run", "view", run_id, "--log", "-R", f"{owner}/{repo}"],
            operation_context=f"fetch logs for run {run_id} in {owner}/{repo}",
            cwd=None,
        )
    except RuntimeError as error:
        return MachineCommandError(
            error_type="logs_unavailable",
            message=str(error),
        )
    except subprocess.SubprocessError as error:
        return MachineCommandError(
            error_type="logs_unavailable",
            message=str(error),
        )

    return result.stdout


@dataclass(frozen=True)
class WorkflowRunListRequest:
    """Request type for workflow run list."""

    limit: int = 20
    actor: str | None = None
    target_repo: str | None = None


@dataclass(frozen=True)
class WorkflowRunListResult:
    """Result for workflow run list."""

    runs: list[dict[str, Any]]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "runs": self.runs,
            "count": len(self.runs),
        }


def run_workflow_run_list(
    ctx: ErkContext,
    request: WorkflowRunListRequest,
) -> WorkflowRunListResult | MachineCommandError:
    if request.limit < 1:
        return MachineCommandError(
            error_type="invalid_request",
            message="limit must be greater than 0",
        )

    resolved_repo = _resolve_repo_target(ctx, target_repo=request.target_repo)
    if isinstance(resolved_repo, MachineCommandError):
        return resolved_repo
    owner, repo = resolved_repo

    repo_root = _get_local_repo_root(ctx)
    if request.target_repo is None and repo_root is not None:
        workflow_runs = ctx.github.list_all_workflow_runs(
            repo_root,
            limit=request.limit,
            actor=request.actor,
        )
    else:
        remote_runs = _list_workflow_runs_remote(
            ctx,
            owner=owner,
            repo=repo,
            limit=request.limit,
            actor=request.actor,
        )
        if isinstance(remote_runs, MachineCommandError):
            return remote_runs
        workflow_runs = remote_runs

    runs = [_serialize_workflow_run(workflow_run, owner=owner, repo=repo) for workflow_run in workflow_runs]
    return WorkflowRunListResult(runs=runs)


@dataclass(frozen=True)
class WorkflowRunStatusRequest:
    """Request type for workflow run status."""

    run_id: str
    target_repo: str | None = None


@dataclass(frozen=True)
class WorkflowRunStatusResult:
    """Result for workflow run status."""

    run: dict[str, Any]

    def to_json_dict(self) -> dict[str, Any]:
        return {"run": self.run}


def run_workflow_run_status(
    ctx: ErkContext,
    request: WorkflowRunStatusRequest,
) -> WorkflowRunStatusResult | MachineCommandError:
    resolved_repo = _resolve_repo_target(ctx, target_repo=request.target_repo)
    if isinstance(resolved_repo, MachineCommandError):
        return resolved_repo
    owner, repo = resolved_repo

    repo_root = _get_local_repo_root(ctx)
    if request.target_repo is None and repo_root is not None:
        workflow_run = ctx.github.get_workflow_run(repo_root, request.run_id)
        if workflow_run is None:
            return MachineCommandError(
                error_type="not_found",
                message=f"Workflow run {request.run_id} not found",
            )
    else:
        remote_run = _get_workflow_run_remote(
            ctx,
            owner=owner,
            repo=repo,
            run_id=request.run_id,
        )
        if isinstance(remote_run, MachineCommandError):
            return remote_run
        workflow_run = remote_run

    return WorkflowRunStatusResult(
        run=_serialize_workflow_run(workflow_run, owner=owner, repo=repo),
    )


@dataclass(frozen=True)
class WorkflowRunLogsRequest:
    """Request type for workflow run logs."""

    run_id: str
    target_repo: str | None = None


@dataclass(frozen=True)
class WorkflowRunLogsResult:
    """Result for workflow run logs."""

    run_id: str
    logs: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "logs": self.logs,
        }


def run_workflow_run_logs(
    ctx: ErkContext,
    request: WorkflowRunLogsRequest,
) -> WorkflowRunLogsResult | MachineCommandError:
    resolved_repo = _resolve_repo_target(ctx, target_repo=request.target_repo)
    if isinstance(resolved_repo, MachineCommandError):
        return resolved_repo
    owner, repo = resolved_repo

    repo_root = _get_local_repo_root(ctx)
    if request.target_repo is None and repo_root is not None:
        try:
            logs = ctx.github.get_run_logs(repo_root, request.run_id)
        except RuntimeError as error:
            return MachineCommandError(
                error_type="logs_unavailable",
                message=str(error),
            )
    else:
        remote_logs = _get_run_logs_remote(
            owner=owner,
            repo=repo,
            run_id=request.run_id,
        )
        if isinstance(remote_logs, MachineCommandError):
            return remote_logs
        logs = remote_logs

    return WorkflowRunLogsResult(run_id=request.run_id, logs=logs)
