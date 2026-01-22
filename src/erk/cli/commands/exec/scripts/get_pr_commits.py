"""Get commits for a PR using REST API (avoids GraphQL rate limits).

Usage:
    erk exec get-pr-commits <PR_NUMBER>

Output:
    JSON with {success, pr_number, commits: [{sha, message, author}]}

Exit Codes:
    0: Success - commits fetched
    1: Error - PR not found or API error
"""

import json
import subprocess

import click

from erk_shared.context.helpers import require_repo_root


@click.command(name="get-pr-commits")
@click.argument("pr_number", type=int)
@click.pass_context
def get_pr_commits(ctx: click.Context, pr_number: int) -> None:
    """Get commits for a PR using REST API (avoids GraphQL rate limits)."""
    repo_root = require_repo_root(ctx)

    # Use gh api with REST endpoint (not gh pr view which uses GraphQL)
    # The REST API endpoint is: GET /repos/{owner}/{repo}/pulls/{pull_number}/commits
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/commits",
            "--jq",
            "[.[] | {sha: .sha, message: .commit.message, author: .commit.author.name}]",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get commits for PR #{pr_number}: {result.stderr.strip()}",
                }
            )
        )
        raise SystemExit(1)

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
