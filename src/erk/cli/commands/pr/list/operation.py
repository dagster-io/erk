"""Core operation for pr list (transport-independent).

Contains the request type and operation function that both the
human command (pr/list_cmd.py) and machine command (json/pr/list_cmd.py) share.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erk.cli.repo_resolution import get_remote_github
from erk.core.context import ErkContext
from erk.core.display_utils import strip_rich_markup
from erk.tui.data.real_provider import RealPrDataProvider
from erk.tui.data.types import PrFilters, PrRowData, serialize_pr_row
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import SortKey
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation, IssueFilterState


@dataclass(frozen=True)
class PrListRequest:
    """Request type for pr list."""

    label: tuple[str, ...] = ()
    state: str | None = None
    run_state: str | None = None
    stage: str | None = None
    limit: int | None = None
    all_users: bool = False
    sort: str = "plan"


@dataclass(frozen=True)
class PrListResult:
    """Result for erk pr list.

    Carries rich PrRowData rows for human display.
    Serialization to JSON dicts happens in to_json_dict().
    """

    rows: list[PrRowData]
    warnings: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        plans = [serialize_pr_row(row) for row in self.rows]
        return {"plans": plans, "count": len(plans)}


def run_pr_list(
    ctx: ErkContext,
    request: PrListRequest,
    *,
    repo_id: GitHubRepoId,
) -> PrListResult | MachineCommandError:
    """Execute pr list operation.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters
        repo_id: Resolved GitHub repo ID

    Returns:
        PrListResult or MachineCommandError
    """
    http_client = ctx.http_client
    if http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication not available",
        )

    # Determine creator filter
    creator: str | None = None
    if not request.all_users:
        remote = get_remote_github(ctx)
        is_authenticated, username, _ = remote.check_auth_status()
        if is_authenticated and username:
            creator = username

    labels = request.label if request.label else ("erk-pr",)

    # Determine location root
    if not isinstance(ctx.repo, NoRepoSentinel):
        root = ctx.repo.root
    else:
        root = Path(tempfile.gettempdir()) / "erk-remote"

    location = GitHubRepoLocation(root=root, repo_id=repo_id)

    provider = RealPrDataProvider(ctx, location=location, http_client=http_client)

    effective_state: IssueFilterState = "closed" if request.state == "closed" else "open"

    filters = PrFilters(
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

    rows, timings = provider.fetch_prs(filters)

    warnings: list[str] = []
    if timings is not None and timings.warnings:
        warnings = list(timings.warnings)

    if request.stage is not None:
        rows = [r for r in rows if strip_rich_markup(r.lifecycle_display).startswith(request.stage)]

    # Sort
    if request.sort == "activity" and not isinstance(ctx.repo, NoRepoSentinel):
        sort_key = SortKey.BRANCH_ACTIVITY
        activity_by_plan = provider.fetch_branch_activity(rows)
        rows = sort_plans(rows, sort_key, activity_by_plan=activity_by_plan)
    else:
        sort_key = SortKey.PLAN_ID
        rows = sort_plans(rows, sort_key)

    return PrListResult(rows=rows, warnings=warnings)
