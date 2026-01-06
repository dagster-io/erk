"""Post an inline review comment on a specific line of a PR.

This exec command creates a pull request review comment attached to a
specific line of a file in the PR diff.

Usage:
    erk exec post-pr-inline-comment --pr-number 123 \\
        --path "src/foo.py" --line 42 --body "Comment text"

Output:
    JSON with success status and comment ID

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec post-pr-inline-comment --pr-number 123 \\
        --path "src/foo.py" --line 42 --body "Use LBYL"
    {"success": true, "comment_id": 12345}

    $ erk exec post-pr-inline-comment --pr-number 123 \\
        --path "bad.py" --line 999 --body "Comment"
    {"success": false, "error_type": "github_api_failed", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.github.parsing import execute_gh_command


@dataclass(frozen=True)
class InlineCommentSuccess:
    """Success response for inline comment posting."""

    success: bool
    comment_id: int


@dataclass(frozen=True)
class InlineCommentError:
    """Error response for inline comment posting."""

    success: bool
    error_type: str
    message: str


def _get_pr_head_sha(repo_root: Path, pr_number: int) -> str:
    """Get the head commit SHA for a PR.

    Uses gh CLI REST API to fetch the PR head ref SHA.
    Uses REST API instead of GraphQL (`gh pr view`) to avoid hitting
    GraphQL rate limits. GraphQL and REST have separate quotas.

    Args:
        repo_root: Repository root directory
        pr_number: PR number to query

    Returns:
        The head commit SHA as a string

    Raises:
        RuntimeError: If gh command fails
    """
    # GH-API-AUDIT: REST - GET pulls/{number}
    cmd = [
        "gh",
        "api",
        f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
        "--jq",
        ".head.sha",
    ]
    stdout = execute_gh_command(cmd, repo_root)
    return stdout.strip()


@click.command(name="post-pr-inline-comment")
@click.option("--pr-number", required=True, type=int, help="PR number to comment on")
@click.option("--path", required=True, help="File path relative to repo root")
@click.option("--line", required=True, type=int, help="Line number in the diff")
@click.option("--body", required=True, help="Comment body text")
@click.pass_context
def post_pr_inline_comment(
    ctx: click.Context, *, pr_number: int, path: str, line: int, body: str
) -> None:
    """Post an inline review comment on a PR.

    Creates a pull request review comment attached to a specific line
    of a file in the PR diff. Automatically fetches the PR head commit SHA.

    PR_NUMBER: The PR to comment on
    PATH: File path relative to repository root
    LINE: Line number in the diff to attach comment to
    BODY: Comment text (markdown supported)
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Get the PR head commit SHA
    try:
        commit_sha = _get_pr_head_sha(repo_root, pr_number)
    except RuntimeError as e:
        result = InlineCommentError(
            success=False,
            error_type="pr-not-found",
            message=f"Could not get PR head commit: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Create the inline comment
    try:
        comment_id = github.create_pr_review_comment(
            repo_root=repo_root,
            pr_number=pr_number,
            body=body,
            commit_sha=commit_sha,
            path=path,
            line=line,
        )
        result_success = InlineCommentSuccess(
            success=True,
            comment_id=comment_id,
        )
        click.echo(json.dumps(asdict(result_success), indent=2))
    except RuntimeError as e:
        result = InlineCommentError(
            success=False,
            error_type="github-api-failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))

    raise SystemExit(0)
