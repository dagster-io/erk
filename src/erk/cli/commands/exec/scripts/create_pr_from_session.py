"""Extract plan from Claude session and create GitHub draft PR.

Usage:
    erk exec create-pr-from-session [--session-id SESSION_ID]

This command combines plan extraction from Claude session files with GitHub
draft PR creation. It extracts the latest ExitPlanMode plan, creates a branch,
commits the plan, and creates a draft PR.

Output:
    JSON result on stdout:
        {"success": true, "plan_number": N, "plan_url": "...", "branch_name": "..."}
    Error messages on stderr with exit code 1 on failure

Exit Codes:
    0: Success - draft PR created
    1: Error - no plan found, gh CLI not available, or other error
"""

import json

import click

from erk_shared.context.helpers import (
    require_branch_manager,
    require_claude_installation,
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_repo_root,
    require_time,
)
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr


@click.command(name="create-pr-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
@click.pass_context
def create_pr_from_session(ctx: click.Context, session_id: str | None) -> None:
    """Extract plan from Claude session and create GitHub draft PR.

    Combines plan extraction with draft PR creation in a single operation.
    """
    # Get dependencies from context
    git = require_git(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    branch_manager = require_branch_manager(ctx)
    time = require_time(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Extract latest plan from session
    plan_text = claude_installation.get_latest_plan(cwd, session_id=session_id)

    if not plan_text:
        result = {"success": False, "error": "No plan found in Claude session files"}
        click.echo(json.dumps(result))
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
        plan_content=plan_text,
        title=None,
        labels=["erk-pr", "erk-plan"],
        source_repo=None,
        objective_id=None,
        created_from_session=session_id,
        created_from_workflow_run_url=None,
        learned_from_issue=None,
        summary=None,
    )

    if not result.success:
        output = {"success": False, "error": result.error}
        click.echo(json.dumps(output))
        raise SystemExit(1)

    # Return success result
    output = {
        "success": True,
        "plan_number": result.plan_number,
        "plan_url": result.plan_url,
        "branch_name": result.branch_name,
        "title": result.title,
    }
    click.echo(json.dumps(output))
