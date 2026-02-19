"""Create .worker-impl/ folder from plan content.

This exec command fetches a plan via PlanBackend and creates the .worker-impl/
folder structure, providing a testable alternative to inline workflow scripts.

Usage:
    erk exec create-worker-impl-from-issue <issue-number>

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.worker-impl/ folder created)
    1: Error (plan not found, fetch failed, folder creation failed)

Examples:
    $ erk exec create-worker-impl-from-issue 1028
    {"success": true, "worker_impl_path": "/path/to/.worker-impl", "issue_number": 1028}

    $ erk exec create-worker-impl-from-issue 999
    {"success": false, "error": "plan_not_found", "message": "..."}
"""

import json

import click

from erk_shared.context.helpers import (
    require_plan_backend,
    require_repo_root,
)
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.worker_impl_folder import create_worker_impl_folder


@click.command(name="create-worker-impl-from-issue")
@click.argument("issue_number", type=int)
@click.pass_context
def create_worker_impl_from_issue(
    ctx: click.Context,
    issue_number: int,
) -> None:
    """Create .worker-impl/ folder from plan content.

    Fetches plan content via PlanBackend and creates .worker-impl/ folder structure
    with plan.md, issue.json, and metadata.

    ISSUE_NUMBER: Plan identifier (e.g., GitHub issue number)
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    plan_id = str(issue_number)

    # Fetch plan via PlanBackend
    result = backend.get_plan(repo_root, plan_id)
    if isinstance(result, PlanNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for issue #{issue_number}: Issue not found. "
            f"Ensure issue has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)
    plan = result

    # Create .worker-impl/ folder with plan content
    worker_impl_path = repo_root / ".worker-impl"
    create_worker_impl_folder(
        plan_content=plan.body,
        plan_id=plan_id,
        url=plan.url,
        repo_root=repo_root,
        objective_id=plan.objective_id,
    )

    # Output structured success result
    output = {
        "success": True,
        "worker_impl_path": str(worker_impl_path),
        "issue_number": issue_number,
        "issue_url": plan.url,
    }
    click.echo(json.dumps(output))
