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
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_branch_manager,
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.impl_folder import create_impl_folder, save_plan_ref
from erk_shared.naming import generate_issue_branch_name
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound


def _get_current_branch(git: Git, cwd: Path) -> str:
    """Get current branch via gateway, raising if detached HEAD."""
    branch = git.branch.get_current_branch(cwd)
    if branch is None:
        msg = "Cannot set up implementation from detached HEAD state"
        raise click.ClickException(msg)
    return branch


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
    plan_backend = require_plan_backend(ctx)
    time = require_time(ctx)

    # Step 1: Fetch plan from GitHub
    result = plan_backend.get_plan(repo_root, str(issue_number))
    if isinstance(result, PlanNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for issue #{issue_number}: Issue not found. "
            f"Ensure issue has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)
    plan = result
    plan_branch = plan.header_fields.get(BRANCH_NAME)

    # Step 2: Determine base branch and create/checkout feature branch
    current_branch = _get_current_branch(git, cwd)

    branch_manager = require_branch_manager(ctx)

    # PLAN_BACKEND_SPLIT: draft-PR plans have branch_name in header_fields; issue-based plans do not
    if isinstance(plan_branch, str) and plan_branch:
        # Draft-PR plan: reuse the plan's existing branch and sync with remote
        branch_name = plan_branch
        git.remote.fetch_branch(repo_root, "origin", branch_name)
        local_branches = git.branch.list_local_branches(repo_root)
        needs_sync = True

        if current_branch == branch_name:
            click.echo(f"Already on plan branch '{branch_name}', syncing with remote...", err=True)
        elif branch_name in local_branches:
            click.echo(f"Checking out plan branch '{branch_name}'...", err=True)
            branch_manager.checkout_branch(cwd, branch_name)
        else:
            click.echo(
                f"Creating local tracking branch for '{branch_name}' from remote...", err=True
            )
            branch_manager.create_tracking_branch(repo_root, branch_name, f"origin/{branch_name}")
            branch_manager.checkout_branch(cwd, branch_name)
            needs_sync = False

        if needs_sync:
            pull_result = git.remote.pull_rebase(cwd, "origin", branch_name)
            if isinstance(pull_result, PullRebaseError):
                error_output = {
                    "success": False,
                    "error": "pull_rebase_failed",
                    "message": (
                        f"Failed to sync branch '{branch_name}' with remote: {pull_result.message}"
                    ),
                }
                click.echo(json.dumps(error_output), err=True)
                raise SystemExit(1)
    else:
        # Issue-based plan: generate P{issue}-... branch name
        # Check if already on a branch for this issue - reuse it
        expected_prefix = f"P{issue_number}-"
        if current_branch.startswith(expected_prefix):
            # Already on correct branch (e.g., remote workflow re-running with issue arg)
            click.echo(f"Already on branch for issue #{issue_number}: {current_branch}", err=True)
            branch_name = current_branch
            # Skip branch creation - just ensure .impl/ exists (handled below)
        else:
            # Generate branch name from issue
            timestamp = time.now()
            branch_name = generate_issue_branch_name(
                issue_number, plan.title, timestamp, objective_id=plan.objective_id
            )

            # Check if branch already exists
            local_branches = git.branch.list_local_branches(repo_root)

            if branch_name in local_branches:
                # Branch exists - just check it out
                click.echo(f"Branch '{branch_name}' already exists, checking out...", err=True)
                branch_manager.checkout_branch(cwd, branch_name)
            else:
                base_branch = current_branch

                # Create branch using BranchManager (handles Graphite tracking automatically)
                create_result = branch_manager.create_branch(repo_root, branch_name, base_branch)
                if isinstance(create_result, BranchAlreadyExists):
                    click.echo(f"Error: {create_result.message}", err=True)
                    raise SystemExit(1) from None
                click.echo(f"Created branch '{branch_name}' from '{base_branch}'", err=True)

                branch_manager.checkout_branch(cwd, branch_name)

    # Step 3: Create .impl/ folder or save plan reference (unless --no-impl)
    impl_path_str: str | None = None

    if not no_impl:
        is_draft_pr_plan = isinstance(plan_branch, str) and plan_branch
        if is_draft_pr_plan:
            # Draft-PR plan: plan.md already lives in impl-context on the branch.
            # Only write plan-ref.json so impl-init can find the issue reference.
            impl_context_dir = cwd / IMPL_CONTEXT_DIR
            impl_path_str = str(impl_context_dir)
            save_plan_ref(
                impl_context_dir,
                provider="github-draft-pr",
                plan_id=str(issue_number),
                url=plan.url,
                labels=(),
                objective_id=plan.objective_id,
            )
        else:
            # Issue-based plan: create .impl/ with full plan content
            impl_path = cwd / ".impl"
            impl_path_str = str(impl_path)

            # Use overwrite=True since we may be re-running after a failed attempt
            create_impl_folder(
                worktree_path=cwd,
                plan_content=plan.body,
                overwrite=True,
            )

            save_plan_ref(
                impl_path,
                provider="github",
                plan_id=str(issue_number),
                url=plan.url,
                labels=(),
                objective_id=plan.objective_id,
            )

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
