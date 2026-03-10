"""Core request/result contract for `erk pr list`."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from erk.core.context import ErkContext
from erk.core.display_utils import strip_rich_markup
from erk.tui.data.real_provider import RealPlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData, serialize_plan_row
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import SortKey
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    IssueFilterState,
)
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub

PrListState = Literal["open", "closed"]
PrListRunState = Literal["queued", "in_progress", "success", "failure", "cancelled"]
PrListStage = Literal["prompted", "planning", "planned", "impl", "merged", "closed"]
PrListSort = Literal["plan", "activity"]


@dataclass(frozen=True)
class PrListRequest:
    """Canonical request for plan listing."""

    labels: tuple[str, ...] = ()
    state: PrListState | None = None
    run_state: PrListRunState | None = None
    stage: PrListStage | None = None
    limit: int | None = None
    all_users: bool = False
    sort: PrListSort = "plan"
    repo: str | None = None


@dataclass(frozen=True)
class PrListResult:
    """Canonical result for plan listing."""

    rows: tuple[PlanRowData, ...]
    warnings: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        plans = [serialize_plan_row(row) for row in self.rows]
        return {"plans": plans, "count": len(plans)}

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "const": True},
                "plans": {"type": "array", "items": {"type": "object"}},
                "count": {"type": "integer"},
            },
            "required": ["count", "plans", "success"],
        }


def run_pr_list(
    request: PrListRequest,
    *,
    ctx: ErkContext,
) -> PrListResult | MachineCommandError:
    """Fetch plans for human or machine adapters."""

    if ctx.http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication not available",
        )

    repo_id_result = _resolve_repo_id(ctx, repo=request.repo)
    if isinstance(repo_id_result, MachineCommandError):
        return repo_id_result

    creator: str | None = None
    if not request.all_users:
        remote = _resolve_remote_github(ctx)
        if isinstance(remote, MachineCommandError):
            return remote
        is_authenticated, username, _ = remote.check_auth_status()
        if is_authenticated and username:
            creator = username

    labels = request.labels if request.labels else ("erk-pr",)
    if not isinstance(ctx.repo, NoRepoSentinel):
        root = ctx.repo.root
    else:
        root = Path(tempfile.gettempdir()) / "erk-remote"

    location = GitHubRepoLocation(root=root, repo_id=repo_id_result)
    provider = RealPlanDataProvider(
        ctx,
        location=location,
        http_client=ctx.http_client,
    )

    effective_state: IssueFilterState = "closed" if request.state == "closed" else "open"
    filters = PlanFilters(
        labels=labels,
        state=effective_state,
        run_state=request.run_state,
        limit=request.limit,
        show_prs=True,
        show_runs=True,
        exclude_labels=(),
        creator=creator,
        show_pr_column=False,
        lifecycle_stage=request.stage,
    )
    rows, timings = provider.fetch_plans(filters)

    if request.stage is not None:
        rows = [
            row
            for row in rows
            if strip_rich_markup(row.lifecycle_display).startswith(request.stage)
        ]

    if request.sort == "activity" and not isinstance(ctx.repo, NoRepoSentinel):
        activity_by_plan = provider.fetch_branch_activity(rows)
        rows = sort_plans(rows, SortKey.BRANCH_ACTIVITY, activity_by_plan=activity_by_plan)
    else:
        rows = sort_plans(rows, SortKey.PLAN_ID)

    warnings = timings.warnings if timings is not None else ()
    return PrListResult(rows=tuple(rows), warnings=tuple(warnings))


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
