"""Set up .erk/impl-context/ folder from GitHub PR in current worktree.

This exec command fetches a plan from a GitHub PR, creates a feature branch,
checks it out, and creates the .erk/impl-context/ folder structure for implementation.

Usage:
    erk exec setup-impl-from-pr <plan-number> [--session-id <id>]

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.erk/impl-context/ folder created, branch checked out)
    1: Error (PR not found, plan fetch failed, git operations failed)

Examples:
    $ erk exec setup-impl-from-pr 1028
    {"success": true, "impl_path": "/path/to/.erk/impl-context",
     "pr_number": 1028, "branch": "P1028-..."}
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_branch_manager,
    require_cwd,
    require_git,
    require_github,
    require_repo_root,
)
from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.schemas import OBJECTIVE_ISSUE
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_folder import (
    create_impl_folder,
    get_impl_dir,
    read_plan_ref,
    resolve_impl_dir,
    save_plan_ref,
)
from erk_shared.plan_store.planned_pr_lifecycle import (
    IMPL_CONTEXT_DIR,
    extract_plan_content,
)


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
    """Fetch, checkout, and teleport a planned-PR plan branch.

    Handles three cases:
    - Already on the branch: just teleport
    - Branch exists locally: checkout and teleport
    - Branch only on remote: create tracking branch (no teleport needed)

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
    needs_teleport = True

    if current_branch == branch_name:
        click.echo(f"Already on PR branch '{branch_name}', teleporting from remote...", err=True)
    elif branch_name in local_branches:
        click.echo(f"Checking out PR branch '{branch_name}'...", err=True)
        branch_manager.checkout_branch(cwd, branch_name)
    else:
        click.echo(f"Creating local tracking branch for '{branch_name}' from remote...", err=True)
        branch_manager.create_tracking_branch(repo_root, branch_name, f"origin/{branch_name}")
        branch_manager.checkout_branch(cwd, branch_name)
        needs_teleport = False

    if needs_teleport:
        pull_result = git.remote.pull_rebase(cwd, "origin", branch_name)
        if isinstance(pull_result, PullRebaseError):
            error_output = {
                "success": False,
                "error": "pull_rebase_failed",
                "message": (
                    f"Failed to teleport branch '{branch_name}' from remote: {pull_result.message}"
                ),
            }
            click.echo(json.dumps(error_output), err=True)
            raise SystemExit(1)


def create_impl_context_from_pr(
    ctx: click.Context,
    *,
    pr_number: int,
    cwd: Path,
    branch_name: str,
) -> dict[str, str | int | bool | None]:
    """Create .erk/impl-context/ folder from a GitHub PR's plan content.

    Fetches PR metadata, reads plan content (from committed .erk/impl-context/
    files or PR body fallback), and creates the impl folder structure.

    Does NOT checkout branches or create worktrees — the caller must already
    be on the correct branch/worktree.

    Args:
        ctx: Click context (for gateway access)
        pr_number: PR number containing the plan
        cwd: Working directory (worktree root)
        branch_name: Branch name for impl-context scoping

    Returns:
        Dict with success status, impl_path, pr_number, pr_url, branch,
        and pr_title.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch PR for PR #{pr_number}: PR not found.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)

    pr_url = pr_result.url

    # Read plan content from committed .erk/impl-context/ files or PR body
    impl_context_dir = repo_root / IMPL_CONTEXT_DIR
    impl_context_plan = impl_context_dir / "plan.md"

    node_ids: tuple[str, ...] | None = None
    if impl_context_plan.exists():
        plan_content = impl_context_plan.read_text(encoding="utf-8")
        ref_json_path = impl_context_dir / "ref.json"
        objective_id: int | None = None
        pr_title: str = pr_result.title
        if ref_json_path.exists():
            ref_data = json.loads(ref_json_path.read_text(encoding="utf-8"))
            raw_objective = ref_data.get("objective_id")
            if isinstance(raw_objective, int):
                objective_id = raw_objective
            raw_title = ref_data.get("title")
            if isinstance(raw_title, str):
                pr_title = raw_title
            raw_node_ids = ref_data.get("node_ids")
            if isinstance(raw_node_ids, list):
                node_ids = tuple(raw_node_ids)
    else:
        # Fallback: extract from PR body (legacy branch or already cleaned up)
        plan_content = extract_plan_content(pr_result.body)
        pr_title = pr_result.title
        objective_id = None
        block = find_metadata_block(pr_result.body, BlockKeys.PLAN_HEADER)
        if block is not None:
            raw_objective = block.data.get(OBJECTIVE_ISSUE)
            if isinstance(raw_objective, int):
                objective_id = raw_objective

    impl_path = get_impl_dir(cwd, branch_name=branch_name)

    create_impl_folder(
        worktree_path=cwd,
        plan_content=plan_content,
        branch_name=branch_name,
        overwrite=True,
    )

    save_plan_ref(
        impl_path,
        provider="github-draft-pr",
        pr_number=str(pr_number),
        url=pr_url,
        labels=(),
        objective_id=objective_id,
        node_ids=node_ids,
    )

    return {
        "success": True,
        "impl_path": str(impl_path),
        "pr_number": pr_number,
        "pr_url": pr_url,
        "branch": branch_name,
        "pr_title": pr_title,
    }


def _setup_planned_pr_plan(
    ctx: click.Context,
    *,
    pr_number: int,
    no_impl: bool,
) -> dict[str, str | int | bool | None]:
    """Set up implementation from a planned-PR plan.

    Uses github.get_pr() for branch discovery, then reads plan content
    from .erk/impl-context/ on the branch (falling back to PR body).

    Args:
        ctx: Click context
        pr_number: PR number for the planned-PR plan
        no_impl: Skip .erk/impl-context/ folder creation

    Returns:
        Success output dict
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)

    # Early exit: if .erk/impl-context/ is already set up for this issue
    # (e.g., CI pre-populated it), skip branch switching. Switching to the
    # plan branch would abandon the implementation branch, causing work to
    # land on the wrong branch.
    current_branch = _get_current_branch(git, cwd)
    impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
    if impl_dir is not None:
        existing_ref = read_plan_ref(impl_dir)
        if existing_ref is not None and existing_ref.pr_id == str(pr_number):
            click.echo(
                f"Found existing impl dir for PR #{pr_number}, skipping branch setup",
                err=True,
            )
            impl_path_str = str(impl_dir) if not no_impl else None
            return {
                "success": True,
                "impl_path": impl_path_str,
                "pr_number": pr_number,
                "pr_url": existing_ref.url,
                "branch": current_branch,
                "pr_title": "",
                "no_impl": no_impl,
            }

    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    branch_manager = require_branch_manager(ctx)

    # Phase A: Lightweight PR query for branch name only
    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch PR for PR #{pr_number}: PR not found.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)

    branch_name = pr_result.head_ref_name
    pr_url = pr_result.url
    current_branch = _get_current_branch(git, cwd)

    # Checkout and teleport the plan branch
    _checkout_plan_branch(
        git=git,
        branch_manager=branch_manager,
        repo_root=repo_root,
        cwd=cwd,
        current_branch=current_branch,
        branch_name=branch_name,
    )

    # Create .erk/impl-context/ folder (unless --no-impl)
    if no_impl:
        return {
            "success": True,
            "impl_path": None,
            "pr_number": pr_number,
            "pr_url": pr_url,
            "branch": branch_name,
            "pr_title": pr_result.title,
            "no_impl": True,
        }

    result = create_impl_context_from_pr(
        ctx,
        pr_number=pr_number,
        cwd=cwd,
        branch_name=branch_name,
    )
    result["no_impl"] = False
    return result


@click.command(name="setup-impl-from-pr")
@click.argument("pr_number", type=int)
@click.option(
    "--session-id",
    default=None,
    help="Claude session ID for marker creation",
)
@click.option(
    "--no-impl",
    is_flag=True,
    help="Skip .erk/impl-context/ folder creation (for local execution without file overhead)",
)
@click.pass_context
def setup_impl_from_pr(
    ctx: click.Context,
    pr_number: int,
    session_id: str | None,
    no_impl: bool,
) -> None:
    """Set up .erk/impl-context/ folder from GitHub PR in current worktree.

    Fetches plan content from GitHub PR, creates/checks out a feature branch,
    and creates .erk/impl-context/ folder structure with plan.md, progress.md, and ref.json.

    PLAN_NUMBER: GitHub PR number containing the plan

    The command:
    1. Fetches the plan from the draft PR
    2. Creates a feature branch from current branch (stacked) or trunk
    3. Checks out the new branch in the current worktree
    4. Creates .erk/impl-context/ folder with plan content
    5. Saves plan reference for PR linking
    """
    output = _setup_planned_pr_plan(ctx, pr_number=pr_number, no_impl=no_impl)
    click.echo(json.dumps(output))
