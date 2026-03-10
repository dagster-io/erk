"""Core operation for pr list.

Pure business logic: takes a request dataclass with simple types,
fetches plan data, and always returns a PrListResult.
No JSON output branching.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from erk.cli.commands.pr.list_cmd import PrListResult
from erk.cli.repo_resolution import get_remote_github, resolve_owner_repo
from erk.core.context import ErkContext
from erk.core.display_utils import strip_rich_markup
from erk.tui.data.real_provider import RealPlanDataProvider
from erk.tui.data.types import PlanFilters, serialize_plan_row
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import SortKey
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation, IssueFilterState
from erk_shared.output.output import user_output


@dataclass(frozen=True)
class PrListRequest:
    """Request for pr list with simple types only."""

    label: tuple[str, ...] = ()
    state: str | None = None
    run_state: str | None = None
    stage: str | None = None
    limit: int | None = None
    all_users: bool = False
    sort: str = "plan"
    repo: str | None = None


def run_pr_list(
    request: PrListRequest,
    *,
    ctx: ErkContext,
) -> PrListResult:
    """Execute pr list and return structured result.

    Always returns PrListResult (never None). Human rendering
    is handled by the human adapter.

    Args:
        request: PrListRequest with simple types
        ctx: ErkContext with all dependencies

    Returns:
        PrListResult with plans and count
    """
    owner, repo_name = resolve_owner_repo(ctx, target_repo=request.repo)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)

    http_client = ctx.http_client
    if http_client is None:
        raise SystemExit(1)

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

    provider = RealPlanDataProvider(ctx, location=location, http_client=http_client)

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

    if timings is not None and timings.warnings:
        for warning in timings.warnings:
            user_output(f"Warning: {warning}")

    if request.stage is not None:
        rows = [r for r in rows if strip_rich_markup(r.lifecycle_display).startswith(request.stage)]

    if not rows:
        return PrListResult(plans=[], count=0)

    # Sort
    if request.sort == "activity" and not isinstance(ctx.repo, NoRepoSentinel):
        sort_key = SortKey.BRANCH_ACTIVITY
        activity_by_plan = provider.fetch_branch_activity(rows)
        rows = sort_plans(rows, sort_key, activity_by_plan=activity_by_plan)
    else:
        sort_key = SortKey.PLAN_ID
        rows = sort_plans(rows, sort_key)

    plans = [serialize_plan_row(row) for row in rows]
    return PrListResult(plans=plans, count=len(plans))
