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

from erk.core.branch_slug_generator import generate_slug_or_fallback
from erk_shared.context.helpers import (
    require_branch_manager,
    require_cwd,
    require_git,
    require_github,
    require_plan_backend,
    require_prompt_executor,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.schemas import OBJECTIVE_ISSUE
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_folder import create_impl_folder, read_plan_ref, save_plan_ref
from erk_shared.naming import (
    InvalidWorktreeName,
    generate_issue_branch_name,
    sanitize_worktree_name,
    validate_worktree_name,
)
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR, extract_plan_content
from erk_shared.plan_store.types import PlanNotFound


def _get_current_branch(git: Git, cwd: Path) -> str:
    """Get current branch via gateway, raising if detached HEAD."""
    branch = git.branch.get_current_branch(cwd)
    if branch is None:
        msg = "Cannot set up implementation from detached HEAD state"
        raise click.ClickException(msg)
    return branch


def _checkout_plan_branch(
    *,
    git: Git,
    branch_manager: BranchManager,
    repo_root: Path,
    cwd: Path,
    current_branch: str,
    branch_name: str,
) -> None:
    """Fetch, checkout, and sync a draft-PR plan branch.

    Handles three cases:
    - Already on the branch: just sync
    - Branch exists locally: checkout and sync
    - Branch only on remote: create tracking branch (no sync needed)

    Args:
        git: Git gateway
        branch_manager: BranchManager for checkout operations
        repo_root: Repository root
        cwd: Current working directory
        current_branch: Name of current branch
        branch_name: Plan branch to checkout
    """
    git.remote.fetch_branch(repo_root, "origin", branch_name)
    local_branches = git.branch.list_local_branches(repo_root)
    needs_sync = True

    if current_branch == branch_name:
        click.echo(f"Already on plan branch '{branch_name}', syncing with remote...", err=True)
    elif branch_name in local_branches:
        click.echo(f"Checking out plan branch '{branch_name}'...", err=True)
        branch_manager.checkout_branch(cwd, branch_name)
    else:
        click.echo(f"Creating local tracking branch for '{branch_name}' from remote...", err=True)
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


def _setup_draft_pr_plan(
    ctx: click.Context,
    *,
    issue_number: int,
    no_impl: bool,
) -> dict[str, str | int | bool | None]:
    """Set up implementation from a draft-PR plan.

    Uses github.get_pr() for branch discovery, then reads plan content
    from .erk/impl-context/ on the branch (falling back to PR body).

    Args:
        ctx: Click context
        issue_number: PR number for the draft-PR plan
        no_impl: Skip .impl/ folder creation

    Returns:
        Success output dict
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)

    # Early exit: if .impl/ is already set up for this issue (e.g., CI pre-populated it),
    # skip branch switching. Switching to the plan branch would abandon the implementation
    # branch, causing work to land on the wrong branch.
    impl_dir = cwd / ".impl"
    if impl_dir.exists():
        existing_ref = read_plan_ref(impl_dir)
        if existing_ref is not None and existing_ref.plan_id == str(issue_number):
            click.echo(
                f"Found existing .impl/ for plan #{issue_number}, skipping branch setup",
                err=True,
            )
            current_branch = _get_current_branch(git, cwd)
            impl_path_str = str(impl_dir) if not no_impl else None
            return {
                "success": True,
                "impl_path": impl_path_str,
                "issue_number": issue_number,
                "issue_url": existing_ref.url,
                "branch": current_branch,
                "plan_title": "",
                "no_impl": no_impl,
            }

    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    branch_manager = require_branch_manager(ctx)

    # Phase A: Lightweight PR query for branch name only
    pr_result = github.get_pr(repo_root, issue_number)
    if isinstance(pr_result, PRNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for PR #{issue_number}: PR not found.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)

    branch_name = pr_result.head_ref_name
    pr_url = pr_result.url
    current_branch = _get_current_branch(git, cwd)

    # Checkout and sync the plan branch
    _checkout_plan_branch(
        git=git,
        branch_manager=branch_manager,
        repo_root=repo_root,
        cwd=cwd,
        current_branch=current_branch,
        branch_name=branch_name,
    )

    # Phase B: After checkout, read plan content from local files or PR body
    impl_context_dir = repo_root / IMPL_CONTEXT_DIR
    impl_context_plan = impl_context_dir / "plan.md"

    if impl_context_plan.exists():
        # Read from committed .erk/impl-context/ files
        plan_content = impl_context_plan.read_text(encoding="utf-8")
        ref_json_path = impl_context_dir / "ref.json"
        objective_id: int | None = None
        plan_title: str = pr_result.title
        if ref_json_path.exists():
            ref_data = json.loads(ref_json_path.read_text(encoding="utf-8"))
            raw_objective = ref_data.get("objective_id")
            if isinstance(raw_objective, int):
                objective_id = raw_objective
            raw_title = ref_data.get("title")
            if isinstance(raw_title, str):
                plan_title = raw_title
        # Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push
    else:
        # Fallback: extract from PR body (legacy branch or already cleaned up)
        plan_content = extract_plan_content(pr_result.body)
        plan_title = pr_result.title
        objective_id = None
        block = find_metadata_block(pr_result.body, "plan-header")
        if block is not None:
            raw_objective = block.data.get(OBJECTIVE_ISSUE)
            if isinstance(raw_objective, int):
                objective_id = raw_objective

    # Create .impl/ folder with plan content (unless --no-impl)
    impl_path_str: str | None = None

    if not no_impl:
        impl_path = cwd / ".impl"
        impl_path_str = str(impl_path)

        create_impl_folder(
            worktree_path=cwd,
            plan_content=plan_content,
            overwrite=True,
        )

        save_plan_ref(
            impl_path,
            provider="github-draft-pr",
            plan_id=str(issue_number),
            url=pr_url,
            labels=(),
            objective_id=objective_id,
        )

    return {
        "success": True,
        "impl_path": impl_path_str,
        "issue_number": issue_number,
        "issue_url": pr_url,
        "branch": branch_name,
        "plan_title": plan_title,
        "no_impl": no_impl,
    }


def _setup_issue_plan(
    ctx: click.Context,
    *,
    issue_number: int,
    no_impl: bool,
) -> dict[str, str | int | bool | None]:
    """Set up implementation from an issue-based plan.

    Uses plan_backend.get_plan() to fetch plan content from a GitHub issue.

    Args:
        ctx: Click context
        issue_number: Issue number for the plan
        no_impl: Skip .impl/ folder creation

    Returns:
        Success output dict
    """
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    plan_backend = require_plan_backend(ctx)
    time = require_time(ctx)

    # Fetch plan from GitHub issue
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

    current_branch = _get_current_branch(git, cwd)
    branch_manager = require_branch_manager(ctx)

    # Issue-based plan: generate P{issue}-... branch name
    # Check if already on a branch for this issue - reuse it
    expected_prefix = f"P{issue_number}-"
    if current_branch.startswith(expected_prefix):
        # Already on correct branch (e.g., remote workflow re-running with issue arg)
        click.echo(f"Already on branch for issue #{issue_number}: {current_branch}", err=True)
        branch_name = current_branch
    else:
        # Generate branch name from issue with LLM-generated slug
        executor = require_prompt_executor(ctx)
        slug = generate_slug_or_fallback(executor, plan.title)
        timestamp = time.now()
        branch_name = generate_issue_branch_name(
            issue_number, slug, timestamp, objective_id=plan.objective_id
        )

        # Validate worktree name derived from branch — agent-facing backpressure gate
        wt_validation = validate_worktree_name(sanitize_worktree_name(branch_name))
        if isinstance(wt_validation, InvalidWorktreeName):
            error_output = {
                "success": False,
                "error": "invalid_worktree_name",
                "message": f"Generated worktree name failed validation.\n"
                f"{wt_validation.format_message()}",
            }
            click.echo(json.dumps(error_output), err=True)
            raise SystemExit(1)

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

    # Create .impl/ folder with plan content (unless --no-impl)
    impl_path_str: str | None = None

    if not no_impl:
        impl_path = cwd / ".impl"
        impl_path_str = str(impl_path)

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

    return {
        "success": True,
        "impl_path": impl_path_str,
        "issue_number": issue_number,
        "issue_url": plan.url,
        "branch": branch_name,
        "plan_title": plan.title,
        "no_impl": no_impl,
    }


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
    1. Fetches the plan from the GitHub issue or draft PR
    2. Creates a feature branch from current branch (stacked) or trunk
    3. Checks out the new branch in the current worktree
    4. Creates .impl/ folder with plan content
    5. Saves issue reference for PR linking
    """
    plan_backend = require_plan_backend(ctx)

    # Dispatch based on plan backend
    if plan_backend.get_provider_name() == "github-draft-pr":
        output = _setup_draft_pr_plan(ctx, issue_number=issue_number, no_impl=no_impl)
    else:
        output = _setup_issue_plan(ctx, issue_number=issue_number, no_impl=no_impl)

    click.echo(json.dumps(output))
