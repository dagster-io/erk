"""Add remote execution note to PR body.

This kit CLI command appends a remote execution tracking note to a PR body.
Used by GitHub Actions workflows to track workflow runs that executed against a PR.

Usage:
    erk kit exec erk add-remote-execution-note --pr-number 123 --run-id 456 --run-url https://...

Output:
    Success message on stdout

Exit Codes:
    0: Success
    1: Error (missing arguments, gh command failed)

Examples:
    $ erk kit exec erk add-remote-execution-note \\
        --pr-number 1895 \\
        --run-id 12345678 \\
        --run-url https://github.com/owner/repo/actions/runs/12345678

    Added remote execution note to PR #1895
"""

import click
from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.github.pr_footer import build_remote_execution_note


@click.command(name="add-remote-execution-note")
@click.option("--pr-number", type=int, required=True, help="PR number to update")
@click.option("--run-id", type=str, required=True, help="Workflow run ID")
@click.option("--run-url", type=str, required=True, help="Full URL to workflow run")
@click.pass_context
def add_remote_execution_note(
    ctx: click.Context, pr_number: int, run_id: str, run_url: str
) -> None:
    """Add remote execution tracking note to PR body.

    Fetches the current PR body, appends a remote execution note with the
    workflow run link, and updates the PR. This creates a history of all
    workflow runs that executed against the PR.

    Args:
        ctx: Click context with GitHub interface
        pr_number: The PR number to update
        run_id: The GitHub Actions workflow run ID
        run_url: Full URL to the workflow run
    """
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    # Get current PR body
    current_body = github.get_pr_body(repo_root, pr_number)
    if current_body is None:
        current_body = ""

    # Build the remote execution note
    remote_note = build_remote_execution_note(run_id, run_url)

    # Append note to body
    new_body = f"{current_body}{remote_note}"

    # Update PR body
    github.update_pr_body(repo_root, pr_number, new_body)

    click.echo(f"Added remote execution note to PR #{pr_number}")
