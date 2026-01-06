"""Create GitHub issue from plan content (via stdin) with erk-plan label.

This exec command handles the complete workflow for creating a plan:
1. Read plan from stdin
2. Extract title from plan
3. Ensure erk-plan label exists
4. Create GitHub issue with plan body and label
5. Return structured JSON result

This replaces the complex shell orchestration in the slash command with a single,
well-tested Python command that uses the ABC interface for GitHub operations.
"""

import json
import sys

import click

from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.github.metadata.core import format_plan_issue_body
from erk_shared.plan_utils import extract_title_from_plan


@click.command(name="create-plan-from-context")
@click.pass_context
def create_plan_from_context(ctx: click.Context) -> None:
    """Create GitHub issue from plan content with erk-plan label.

    Reads plan content from stdin, extracts title, ensures erk-plan label exists,
    creates issue with collapsible plan body and execution commands, and returns JSON result.

    Workflow:
    1. Create issue with plan body wrapped in collapsible metadata block
    2. Update issue body to include execution commands (using returned issue number)

    Usage:
        echo "$plan" | erk exec create-plan-from-context

    Exit Codes:
        0: Success
        1: Error (empty plan, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}
    """
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read plan from stdin
    plan = sys.stdin.read()

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Extract title (pure function call)
    title = extract_title_from_plan(plan)

    # Initial body: just the plan content (without commands, since we don't have issue number yet)
    # We'll update it after creation with the full formatted body including commands
    initial_body = plan.strip()

    # Ensure label exists (ABC interface)
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
    except RuntimeError as e:
        click.echo(f"Error: Failed to ensure label exists: {e}", err=True)
        raise SystemExit(1) from e

    # Create issue (ABC interface with EAFP pattern)
    # Add [erk-plan] suffix to title for visibility
    issue_title = f"{title} [erk-plan]"
    try:
        result = github.create_issue(
            repo_root=repo_root, title=issue_title, body=initial_body, labels=["erk-plan"]
        )
    except RuntimeError as e:
        click.echo(f"Error: Failed to create GitHub issue: {e}", err=True)
        raise SystemExit(1) from e

    # Now that we have the issue number, format the complete body with commands
    formatted_body = format_plan_issue_body(plan.strip(), result.number)

    # Update the issue body with the formatted version
    try:
        github.update_issue_body(repo_root, result.number, formatted_body)
    except RuntimeError as e:
        click.echo(f"Error: Failed to update issue body: {e}", err=True)
        raise SystemExit(1) from e

    # Output structured JSON
    output = {
        "success": True,
        "issue_number": result.number,
        "issue_url": result.url,
    }
    click.echo(json.dumps(output))
