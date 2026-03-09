"""Serialize plan dashboard data to JSON for external consumers.

Usage:
    erk exec dash-data [--state open|closed] [--label LABEL] [--limit N]
        [--show-prs/--no-show-prs] [--show-runs/--no-show-runs]
        [--run-state STATE] [--creator USER]

Output:
    JSON with {success, plans, count}

Exit Codes:
    0: Success
    1: Error (missing repo info, API error)
"""

import json

import click

from erk.cli.core import discover_repo_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.tui.data.real_provider import RealPlanDataProvider
from erk.tui.data.types import PlanFilters, serialize_plan_row
from erk_shared.context.helpers import require_context
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation, IssueFilterState


@click.command(name="dash-data")
@click.option("--state", type=click.Choice(["open", "closed"]), default=None)
@click.option("--label", multiple=True, default=("erk-pr",))
@click.option("--limit", type=int, default=None)
@click.option("--show-prs/--no-show-prs", default=True)
@click.option("--show-runs/--no-show-runs", default=False)
@click.option("--run-state", default=None)
@click.option("--creator", default=None)
@click.pass_context
def dash_data(
    ctx: click.Context,
    *,
    state: str | None,
    label: tuple[str, ...],
    limit: int | None,
    show_prs: bool,
    show_runs: bool,
    run_state: str | None,
    creator: str | None,
) -> None:
    """Serialize plan dashboard data to JSON."""
    erk_ctx = require_context(ctx)

    repo = discover_repo_context(erk_ctx, erk_ctx.cwd)
    ensure_erk_metadata_dir(repo)

    if repo.github is None:
        click.echo(
            json.dumps({"success": False, "error": "Could not determine repository owner/name"})
        )
        raise SystemExit(1)

    location = GitHubRepoLocation(
        root=repo.root,
        repo_id=GitHubRepoId(repo.github.owner, repo.github.repo),
    )

    http_client = erk_ctx.http_client
    if http_client is None:
        click.echo(json.dumps({"success": False, "error": "GitHub authentication not available"}))
        raise SystemExit(1)

    provider = RealPlanDataProvider(
        erk_ctx,
        location=location,
        http_client=http_client,
    )

    effective_state: IssueFilterState = "closed" if state == "closed" else "open"

    filters = PlanFilters(
        labels=label,
        state=effective_state,
        run_state=run_state,
        limit=limit,
        show_prs=show_prs,
        show_runs=show_runs,
        exclude_labels=(),
        creator=creator,
    )

    rows, _timings = provider.fetch_plans(filters)
    plans = [serialize_plan_row(row) for row in rows]

    click.echo(json.dumps({"success": True, "plans": plans, "count": len(plans)}))
