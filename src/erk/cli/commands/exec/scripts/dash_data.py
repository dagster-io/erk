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

import dataclasses
import json
from datetime import datetime
from typing import Any

import click

from erk.cli.core import discover_repo_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.tui.data.types import PlanFilters, PlanRowData
from erk_shared.context.helpers import require_context
from erk_shared.gateway.browser.real import RealBrowserLauncher
from erk_shared.gateway.clipboard.real import RealClipboard
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.gateway.http.auth import fetch_github_token
from erk_shared.gateway.http.real import RealHttpClient
from erk_shared.gateway.plan_data_provider.real import RealPlanDataProvider


def _serialize_plan_row(row: PlanRowData) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict.

    Handles datetime fields (to ISO 8601 strings) and tuple fields
    (log_entries) to lists for JSON compatibility.
    """
    data = dataclasses.asdict(row)
    for key in ("last_local_impl_at", "last_remote_impl_at", "updated_at", "created_at"):
        if isinstance(data[key], datetime):
            data[key] = data[key].isoformat()
    # Convert log_entries tuple of tuples to list of lists
    data["log_entries"] = [list(entry) for entry in row.log_entries]
    return data


@click.command(name="dash-data")
@click.option("--state", type=click.Choice(["open", "closed"]), default=None)
@click.option("--label", multiple=True, default=("erk-plan",))
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

    provider = RealPlanDataProvider(
        erk_ctx,
        location=location,
        clipboard=RealClipboard(),
        browser=RealBrowserLauncher(),
        http_client=RealHttpClient(token=fetch_github_token(), base_url="https://api.github.com"),
    )

    filters = PlanFilters(
        labels=label,
        state=state,
        run_state=run_state,
        limit=limit,
        show_prs=show_prs,
        show_runs=show_runs,
        creator=creator,
    )

    rows = provider.fetch_plans(filters)
    plans = [_serialize_plan_row(row) for row in rows]

    click.echo(json.dumps({"success": True, "plans": plans, "count": len(plans)}))
