"""Set up .impl/ folder from GitHub issue in current worktree.

This exec command fetches a plan from a GitHub issue, creates a feature branch,
checks it out, and creates the .impl/ folder structure for implementation.

Usage:
    erk exec setup-impl-from-issue <issue-number> [--session-id <id>]

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.impl/ folder created, branch checked out)
    1: Error (issue not found, plan fetch failed, git operations failed)

Examples:
    $ erk exec setup-impl-from-issue 1028
    {"success": true, "impl_path": "/path/to/.impl", "issue_number": 1028, "branch": "P1028-..."}
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import click

from erk_shared.context.helpers import require_cwd, require_git, require_repo_root
from erk_shared.gateway.time.real import RealTime
from erk_shared.git.abc import Git
from erk_shared.github.issues import RealGitHubIssues
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.naming import generate_issue_branch_name
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.prompt_executor.real import RealPromptExecutor


def _get_current_branch(git: Git, cwd: Path) -> str:
    """Get current branch via gateway, raising if detached HEAD."""
    branch = git.get_current_branch(cwd)
    if branch is None:
        msg = "Cannot set up implementation from detached HEAD state"
        raise click.ClickException(msg)
    return branch


def _is_trunk_branch(branch: str) -> bool:
    """Check if branch is a trunk branch (main/master)."""
    return branch in ("main", "master")


@click.command(name="setup-impl-from-issue")
@click.argument("issue_number", type=int)
@click.option(
    "--session-id",
    default=None,
    help="Claude session ID for marker creation",
)
@click.option(
    "--no-impl",
    is_flag=True,
    help="Skip .impl/ folder creation (for local execution without file overhead)",
)
@click.pass_context
def setup_impl_from_issue(
    ctx: click.Context,
    issue_number: int,
    session_id: str | None,
    no_impl: bool,
) -> None:
    """Set up .impl/ folder from GitHub issue in current worktree.

    Fetches plan content from GitHub issue, creates/checks out a feature branch,
    and creates .impl/ folder structure with plan.md, progress.md, and issue.json.

    ISSUE_NUMBER: GitHub issue number containing the plan

    The command:
    1. Fetches the plan from the GitHub issue
    2. Creates a feature branch from current branch (stacked) or trunk
    3. Checks out the new branch in the current worktree
    4. Creates .impl/ folder with plan content
    5. Saves issue reference for PR linking
    """
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    # Direct instantiation of required dependencies
    time = RealTime()
    github_issues = RealGitHubIssues(target_repo=None)
    plan_store = GitHubPlanStore(github_issues, time)
    prompt_executor = RealPromptExecutor(time)

    # Step 1: Fetch plan from GitHub
    try:
        plan = plan_store.get_plan(repo_root, str(issue_number))
    except RuntimeError as e:
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for issue #{issue_number}: {e}. "
            f"Ensure issue has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1) from e

    # Step 2: Determine base branch and create feature branch
    current_branch = _get_current_branch(git, cwd)

    # Generate branch name from issue
    timestamp = datetime.now(UTC)
    branch_name = generate_issue_branch_name(issue_number, plan.title, timestamp)

    # Check if branch already exists
    local_branches = git.list_local_branches(repo_root)

    if branch_name in local_branches:
        # Branch exists - just check it out
        click.echo(f"Branch '{branch_name}' already exists, checking out...", err=True)
        git.checkout_branch(cwd, branch_name)
    else:
        # Determine base branch: stack on feature branch, or use trunk
        if _is_trunk_branch(current_branch):
            base_branch = current_branch
        else:
            # Stack on current feature branch
            base_branch = current_branch

        # Create and checkout branch
        git.create_branch(repo_root, branch_name, base_branch)
        git.checkout_branch(cwd, branch_name)
        click.echo(f"Created branch '{branch_name}' from '{base_branch}'", err=True)

    # Step 3: Create .impl/ folder with plan content (unless --no-impl)
    impl_path_str: str | None = None

    if not no_impl:
        impl_path = cwd / ".impl"
        impl_path_str = str(impl_path)

        # Use overwrite=True since we may be re-running after a failed attempt
        create_impl_folder(
            worktree_path=cwd,
            plan_content=plan.body,
            prompt_executor=prompt_executor,
            overwrite=True,
        )

        # Step 4: Save issue reference for PR linking
        save_issue_reference(impl_path, issue_number, plan.url, plan.title)

    # Output structured success result
    output: dict[str, str | int | bool | None] = {
        "success": True,
        "impl_path": impl_path_str,
        "issue_number": issue_number,
        "issue_url": plan.url,
        "branch": branch_name,
        "plan_title": plan.title,
        "no_impl": no_impl,
    }
    click.echo(json.dumps(output))
