"""Create .erk/impl-context/ folder from plan content.

This exec command fetches a plan via ManagedPrBackend and creates the .erk/impl-context/
folder structure, providing a testable alternative to inline workflow scripts.

Usage:
    erk exec create-impl-context-from-plan <plan-id>

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.erk/impl-context/ folder created)
    1: Error (plan not found, fetch failed, folder creation failed)

Examples:
    $ erk exec create-impl-context-from-plan 1028
    {"success": true, "impl_context_path": "/path/to/.erk/impl-context", "pr_number": 1028}

    $ erk exec create-impl-context-from-plan 999
    {"success": false, "error": "plan_not_found", "message": "..."}
"""

import json

import click

from erk_shared.context.helpers import (
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.impl_context import create_impl_context
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound


@click.command(name="create-impl-context-from-plan")
@click.argument("pr_number", type=int)
@click.pass_context
def create_impl_context_from_plan(
    ctx: click.Context,
    pr_number: int,
) -> None:
    """Create .erk/impl-context/ folder from plan content.

    Fetches plan content via ManagedPrBackend and creates .erk/impl-context/ folder structure
    with plan.md and ref.json metadata.

    PLAN_ID: Plan identifier (e.g., GitHub issue number or PR number)
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    time = require_time(ctx)
    pr_id = str(pr_number)
    provider = backend.get_provider_name()

    # Fetch plan via ManagedPrBackend
    result = backend.get_managed_pr(repo_root, pr_id)
    if isinstance(result, PlanNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch PR for #{pr_number}: Not found. "
            f"Ensure PR has erk-pr label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)
    plan = result

    # Create .erk/impl-context/ folder with plan content
    impl_context_path = repo_root / IMPL_CONTEXT_DIR
    create_impl_context(
        plan_content=plan.body,
        plan_id=pr_id,
        url=plan.url,
        repo_root=repo_root,
        provider=provider,
        objective_id=plan.objective_id,
        now_iso=time.now().isoformat(),
        node_ids=None,
    )

    # Output structured success result
    output = {
        "success": True,
        "impl_context_path": str(impl_context_path),
        "pr_number": pr_number,
        "pr_url": plan.url,
    }
    click.echo(json.dumps(output))
