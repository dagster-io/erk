#!/usr/bin/env python3
"""Update PR body with implementation summary from commit message.

This command updates a PR body with the implementation summary extracted from
a commit message, plus a standardized footer with checkout instructions.

This replaces ~20 lines of bash (git log, heredoc assembly, gh pr edit) in
GitHub Actions workflows.

Usage:
    erk exec update-pr-summary \\
        --branch-name my-feature-branch \\
        --issue-number 123 \\
        --commit-sha abc123def

Output:
    JSON object with success status

Exit Codes:
    0: Success (PR body updated)
    1: Error (git command failed, PR not found, or GitHub API failed)

Examples:
    $ erk exec update-pr-summary \\
        --branch-name feat-auth \\
        --issue-number 456 \\
        --commit-sha abc123
    {
      "success": true,
      "pr_number": 789
    }
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_git, require_github, require_repo_root
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound


@dataclass(frozen=True)
class UpdateSuccess:
    """Success result when PR body is updated."""

    success: bool
    pr_number: int


@dataclass(frozen=True)
class UpdateError:
    """Error result when PR body update fails."""

    success: bool
    error: str
    message: str


def _build_pr_body(commit_message: str, pr_number: int, issue_number: int) -> str:
    """Build the PR body with summary and footer.

    Args:
        commit_message: Full commit message to use as summary
        pr_number: PR number for checkout instructions
        issue_number: Issue number to close on merge

    Returns:
        Formatted PR body markdown
    """
    footer = build_pr_body_footer(pr_number=pr_number, issue_number=issue_number)
    return f"""## Summary

{commit_message}
{footer}"""


@click.command(name="update-pr-summary")
@click.option("--branch-name", type=str, required=True, help="Branch name to look up PR")
@click.option("--issue-number", type=int, required=True, help="Issue number to close on merge")
@click.option("--commit-sha", type=str, required=True, help="Commit SHA to extract message from")
@click.pass_context
def update_pr_summary(
    ctx: click.Context,
    branch_name: str,
    issue_number: int,
    commit_sha: str,
) -> None:
    """Update PR body with implementation summary from commit message.

    Extracts the full commit message from the specified commit SHA, builds
    a PR body with summary and standardized footer, and updates the PR.
    """
    git = require_git(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    # Get full commit message using Git ABC
    commit_message = git.get_commit_message(repo_root, commit_sha)
    if commit_message is None:
        result = UpdateError(
            success=False,
            error="commit_not_found",
            message=f"Could not find commit {commit_sha}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    # Get PR for branch using GitHub ABC
    pr_result = github.get_pr_for_branch(repo_root, branch_name)
    if isinstance(pr_result, PRNotFound):
        result = UpdateError(
            success=False,
            error="pr_not_found",
            message=f"No PR found for branch {branch_name}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    pr_number = pr_result.number

    # Build and update PR body
    pr_body = _build_pr_body(commit_message, pr_number, issue_number)

    try:
        github.update_pr_body(repo_root, pr_number, pr_body)
        result = UpdateSuccess(success=True, pr_number=pr_number)
        click.echo(json.dumps(asdict(result), indent=2))
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from e
