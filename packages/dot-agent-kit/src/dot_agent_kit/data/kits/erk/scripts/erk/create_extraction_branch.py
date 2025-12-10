"""Create and push a branch for extraction documentation.

Usage:
    erk kit exec erk create-extraction-branch \
        --issue-number 123 \
        --trunk-branch master

This command:
1. Checks out the trunk branch
2. Pulls latest changes
3. Creates a new branch named extraction-docs-{issue_number}
4. Pushes the branch with upstream tracking

Output:
    JSON with success status and branch_name
"""

import json
from pathlib import Path

import click
from erk_shared.context.helpers import require_git, require_repo_root


@click.command(name="create-extraction-branch")
@click.option(
    "--issue-number",
    type=int,
    required=True,
    help="GitHub issue number",
)
@click.option(
    "--trunk-branch",
    type=str,
    required=True,
    help="Name of trunk branch (main/master)",
)
@click.pass_context
def create_extraction_branch(
    ctx: click.Context,
    issue_number: int,
    trunk_branch: str,
) -> None:
    """Create and push a branch for extraction documentation.

    Creates a new branch from the trunk branch for implementing
    documentation extraction from a GitHub issue.
    """
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)
    cwd = Path.cwd()

    branch_name = f"extraction-docs-P{issue_number}"

    # Check if branch already exists locally
    local_branches = git.list_local_branches(repo_root)
    if branch_name in local_branches:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Branch {branch_name} already exists locally",
                }
            )
        )
        raise SystemExit(1)

    # Checkout trunk branch
    try:
        git.checkout_branch(cwd, trunk_branch)
    except Exception as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to checkout {trunk_branch}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Pull latest from trunk
    try:
        git.pull_branch(repo_root, "origin", trunk_branch, ff_only=True)
    except Exception as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to pull {trunk_branch}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Create and checkout new branch
    try:
        git.create_branch(cwd, branch_name, trunk_branch)
        git.checkout_branch(cwd, branch_name)
    except Exception as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to create branch {branch_name}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Push with upstream tracking
    try:
        git.push_to_remote(cwd, "origin", branch_name, set_upstream=True)
    except Exception as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to push branch {branch_name}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "branch_name": branch_name,
                "issue_number": issue_number,
            }
        )
    )


if __name__ == "__main__":
    create_extraction_branch()
