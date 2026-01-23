"""Fetch PR commits using REST API (avoids GraphQL rate limits).

Usage:
    erk exec get-pr-commits <PR_NUMBER>

Output:
    JSON with {success, pr_number, commits: [{sha, message}]}

Exit Codes:
    0: Success - commits fetched
    1: Error - PR not found or API error
"""

import json

import click

from erk_shared.context.helpers import require_cwd
from erk_shared.subprocess_utils import run_subprocess_with_context


@click.command(name="get-pr-commits")
@click.argument("pr_number", type=int)
@click.pass_context
def get_pr_commits(ctx: click.Context, pr_number: int) -> None:
    """Fetch PR commits using REST API (avoids GraphQL rate limits)."""
    cwd = require_cwd(ctx)

    # Use gh api to get commits from REST API
    # The endpoint is /repos/{owner}/{repo}/pulls/{pull_number}/commits
    # gh api handles owner/repo detection from the current directory
    try:
        result = run_subprocess_with_context(
            cmd=[
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/commits",
                "--jq",
                "[.[] | {sha: .sha, message: .commit.message}]",
            ],
            operation_context=f"get commits for PR #{pr_number}",
            cwd=cwd,
        )
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get commits for PR #{pr_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Parse the JSON output from gh api
    commits = json.loads(result.stdout)

    click.echo(
        json.dumps(
            {
                "success": True,
                "pr_number": pr_number,
                "commits": commits,
            }
        )
    )
