#!/usr/bin/env python3
"""Post multiple comments to a GitHub issue.

This command takes JSON with comment_bodies array from stdin (from render-session-content)
and posts each as a separate comment to the specified issue.

Usage:
    echo '{"comment_bodies": ["body1"]}' | dot-agent run erk post-issue-comments --issue-number 123

Output:
    JSON object with success status, issue number, and count of comments posted

Exit Codes:
    0: Success
    1: Error (invalid input, missing issue number, or GitHub API failure)

Examples:
    $ echo '{"comment_bodies": ["Comment 1", "Comment 2"]}' | \
        dot-agent run erk post-issue-comments --issue-number 123
    {
      "success": true,
      "issue_number": 123,
      "comments_posted": 2
    }
"""

import json
import sys

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


@click.command(name="post-issue-comments")
@click.option(
    "--issue-number",
    required=True,
    type=int,
    help="GitHub issue number to post comments to",
)
@click.pass_context
def post_issue_comments(ctx: click.Context, issue_number: int) -> None:
    """Post multiple comments to a GitHub issue.

    Reads JSON with comment_bodies array from stdin and posts each
    as a separate comment to the specified issue.
    """
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read from stdin
    if sys.stdin.isatty():
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "No input provided",
                    "help": "Pipe JSON with comment_bodies array from render-session-content",
                }
            )
        )
        raise SystemExit(1)

    input_text = sys.stdin.read()

    # Parse JSON input
    try:
        input_data = json.loads(input_text)
    except json.JSONDecodeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {e}",
                    "help": "Input must be valid JSON with comment_bodies array",
                }
            )
        )
        raise SystemExit(1) from e

    # Validate input structure - support both direct array and nested structure
    comment_bodies: list[str] = []
    if isinstance(input_data, list):
        comment_bodies = input_data
    elif isinstance(input_data, dict):
        comment_bodies = input_data.get("comment_bodies", [])
    else:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Invalid input structure",
                    "help": "Input must be JSON array or object with comment_bodies array",
                }
            )
        )
        raise SystemExit(1)

    if not comment_bodies:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "No comment_bodies provided",
                    "help": "Input must contain non-empty comment_bodies array",
                }
            )
        )
        raise SystemExit(1)

    # Validate all bodies are strings
    for i, body in enumerate(comment_bodies):
        if not isinstance(body, str):
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": f"comment_bodies[{i}] is not a string",
                        "help": "All comment bodies must be strings",
                    }
                )
            )
            raise SystemExit(1)

    # Post each comment
    comments_posted = 0
    for body in comment_bodies:
        github_issues.add_comment(repo_root, issue_number, body)
        comments_posted += 1

    result = {
        "success": True,
        "issue_number": issue_number,
        "comments_posted": comments_posted,
    }

    click.echo(json.dumps(result, indent=2))
