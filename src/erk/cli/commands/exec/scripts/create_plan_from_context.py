"""Create GitHub draft PR from plan content (via stdin) with erk-plan label.

This exec command handles the complete workflow for creating a plan:
1. Read plan from stdin
2. Create a branch from origin/trunk
3. Commit plan.md + ref.json to branch via git plumbing
4. Push branch and create draft PR
5. Return structured JSON result
"""

import json
import sys

import click

from erk_shared.context.helpers import (
    require_branch_manager,
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_repo_root,
    require_time,
)
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr


@click.command(name="create-plan-from-context")
@click.pass_context
def create_plan_from_context(ctx: click.Context) -> None:
    """Create GitHub draft PR from plan content with erk-plan label.

    Reads plan content from stdin, creates a branch, commits plan files,
    pushes, and creates a draft PR. Returns JSON result.

    Usage:
        echo "$plan" | erk exec create-plan-from-context

    Exit Codes:
        0: Success
        1: Error (empty plan, gh failure, etc.)

    Output:
        JSON object: {"success": true, "plan_number": 123, "plan_url": "...", "branch_name": "..."}
    """
    # Get dependencies from context
    git = require_git(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    branch_manager = require_branch_manager(ctx)
    time = require_time(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)

    # Read plan from stdin
    plan = sys.stdin.read()

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Create plan as a draft PR
    result = create_plan_draft_pr(
        git=git,
        github=github,
        github_issues=github_issues,
        branch_manager=branch_manager,
        time=time,
        repo_root=repo_root,
        cwd=cwd,
        plan_content=plan,
        title=None,
        labels=["erk-pr", "erk-plan"],
        source_repo=None,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=None,
    )

    if not result.success:
        click.echo(f"Error: {result.error}", err=True)
        raise SystemExit(1)

    # Output structured JSON
    output = {
        "success": True,
        "plan_number": result.plan_number,
        "plan_url": result.plan_url,
        "branch_name": result.branch_name,
    }
    click.echo(json.dumps(output))
