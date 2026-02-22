"""Create .erk/impl-context/ folder from plan content.

This exec command fetches a plan via PlanBackend and creates the .erk/impl-context/
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
    {"success": true, "impl_context_path": "/path/to/.erk/impl-context", "plan_id": 1028}

    $ erk exec create-impl-context-from-plan 999
    {"success": false, "error": "plan_not_found", "message": "..."}
"""

import json

import click

from erk_shared.context.helpers import (
    require_plan_backend,
    require_repo_root,
)
from erk_shared.impl_context import create_impl_context
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound


@click.command(name="create-impl-context-from-plan")
@click.argument("plan_id", type=int)
@click.pass_context
def create_impl_context_from_plan(
    ctx: click.Context,
    plan_id: int,
) -> None:
    """Create .erk/impl-context/ folder from plan content.

    Fetches plan content via PlanBackend and creates .erk/impl-context/ folder structure
    with plan.md and ref.json metadata.

    PLAN_ID: Plan identifier (e.g., GitHub issue number or PR number)
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    plan_id_str = str(plan_id)
    provider = backend.get_provider_name()

    # Fetch plan via PlanBackend
    result = backend.get_plan(repo_root, plan_id_str)
    if isinstance(result, PlanNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for #{plan_id}: Not found. "
            f"Ensure plan has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)
    plan = result

    # Create .erk/impl-context/ folder with plan content
    impl_context_path = repo_root / IMPL_CONTEXT_DIR
    create_impl_context(
        plan_content=plan.body,
        plan_id=plan_id_str,
        url=plan.url,
        repo_root=repo_root,
        provider=provider,
        objective_id=plan.objective_id,
    )

    # Output structured success result
    output = {
        "success": True,
        "impl_context_path": str(impl_context_path),
        "plan_id": plan_id,
        "plan_url": plan.url,
    }
    click.echo(json.dumps(output))
