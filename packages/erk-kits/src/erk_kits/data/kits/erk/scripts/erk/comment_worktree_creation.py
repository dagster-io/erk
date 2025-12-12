"""Post GitHub comment documenting worktree creation.

This kit CLI command wraps add_worktree_creation_comment() for agent invocation.

Usage:
    erk kit exec erk comment-worktree-creation <issue_number> <worktree_name> <branch_name>

Output:
    Silent on success (agent shows its own success message)
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (not in git repo, gh CLI failure, or issue not found)

Examples:
    $ erk kit exec erk comment-worktree-creation 123 feature-name feature-branch
"""

import click

from erk.kits.context_helpers import require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.impl_folder import add_worktree_creation_comment


@click.command(name="comment-worktree-creation")
@click.argument("issue_number", type=int)
@click.argument("worktree_name")
@click.argument("branch_name")
@click.pass_context
def comment_worktree_creation(
    ctx: click.Context, issue_number: int, worktree_name: str, branch_name: str
) -> None:
    """Post GitHub comment documenting worktree creation.

    ISSUE_NUMBER: GitHub issue number to comment on
    WORKTREE_NAME: Name of the created worktree
    BRANCH_NAME: Git branch name for the worktree
    """
    # Get dependencies from context
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Post comment
    try:
        add_worktree_creation_comment(
            github_issues, repo_root, issue_number, worktree_name, branch_name
        )
    except RuntimeError as e:
        click.echo(
            click.style("Error: ", fg="red") + f"Failed to post comment: {e}",
            err=True,
        )
        raise SystemExit(1) from e

    # Silent success - agent will show its own success message
