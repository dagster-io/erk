"""Extract plan from Claude session and create GitHub issue.

Usage:
    erk exec create-issue-from-session [--session-id SESSION_ID]

This command combines plan extraction from Claude session files with GitHub
issue creation. It extracts the latest ExitPlanMode plan, ensures the erk-plan
label exists, and creates a GitHub issue with the plan content.

SCHEMA VERSION 2: This command uses the new two-step creation flow:
1. Create issue with metadata-only body (using format_plan_header_body())
2. Add first comment with plan content (using format_plan_content_comment())

Output:
    JSON result on stdout: {"success": true, "issue_number": N, "issue_url": "..."}
    Error messages on stderr with exit code 1 on failure

Exit Codes:
    0: Success - issue created
    1: Error - no plan found, gh CLI not available, or other error
"""

import json

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_repo_root,
    require_session_store,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.github.plan_issues import create_plan_issue


@click.command(name="create-issue-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
@click.pass_context
def create_issue_from_session(ctx: click.Context, session_id: str | None) -> None:
    """Extract plan from Claude session and create GitHub issue.

    Combines plan extraction with GitHub issue creation in a single operation.

    Schema Version 2 format:
    - Issue body: metadata-only (schema_version, created_at, created_by, worktree_name)
    - First comment: plan content wrapped in markers
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    session_store = require_session_store(ctx)

    # Extract latest plan from session
    plan_text = session_store.get_latest_plan(cwd, session_id=session_id)

    if not plan_text:
        result = {"success": False, "error": "No plan found in Claude session files"}
        click.echo(json.dumps(result))
        raise SystemExit(1)

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=plan_text,
        title=None,
        plan_type=None,
        extra_labels=None,
        title_suffix=None,
        source_plan_issues=None,
        extraction_session_ids=None,
        source_repo=None,
        objective_issue=None,
    )

    if not result.success:
        if result.issue_number is not None:
            # Partial success - issue created but comment failed
            output = {
                "success": False,
                "error": result.error,
                "issue_number": result.issue_number,
                "issue_url": result.issue_url,
            }
        else:
            output = {"success": False, "error": result.error}
        click.echo(json.dumps(output))
        raise SystemExit(1)

    # Return success result
    output = {
        "success": True,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
        "title": result.title,
    }
    click.echo(json.dumps(output))
