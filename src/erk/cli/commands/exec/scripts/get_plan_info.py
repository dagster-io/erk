"""Backend-aware plan info retrieval.

Usage:
    erk exec get-plan-info <plan-number>
    erk exec get-plan-info <plan-number> --include-body

Output:
    JSON with plan info fields:
    {"success": true, "pr_number": "42", "title": "...", "state": "OPEN",
     "labels": [...], "url": "...", "objective_id": null, "backend": "github",
     "head_ref_name": "...", "base_ref_name": "..."}

    With --include-body, adds "body": "..." containing plan content.

Exit Codes:
    0: Success
    1: Error (plan not found)
"""

import json

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.plan_store.types import PlanNotFound


@click.command(name="get-plan-info")
@click.argument("pr_number", type=int)
@click.option(
    "--include-body",
    is_flag=True,
    help="Include the PR body content in the response",
)
@click.pass_context
def get_plan_info(
    ctx: click.Context,
    pr_number: int,
    *,
    include_body: bool,
) -> None:
    """Retrieve plan info from the appropriate backend."""
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    pr_id = str(pr_number)

    plan = backend.get_managed_pr(repo_root, pr_id)
    if isinstance(plan, PlanNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "plan_not_found",
                    "message": f"PR #{pr_number} not found",
                }
            ),
            err=True,
        )
        raise SystemExit(1)

    result: dict[str, object] = {
        "success": True,
        "pr_number": plan.pr_identifier,
        "title": plan.title,
        "state": plan.state.value,
        "labels": plan.labels,
        "url": plan.url,
        "objective_id": plan.objective_id,
        "backend": backend.get_provider_name(),
        "head_ref_name": plan.metadata.get("head_ref_name"),
        "base_ref_name": plan.metadata.get("base_ref_name"),
    }

    if include_body:
        result["body"] = plan.body

    click.echo(json.dumps(result))
