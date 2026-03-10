"""Consolidated implementation setup command for plan-implement.

Replaces the entire Steps 0-2d decision tree in plan-implement.md with a
single command. Handles argument parsing, source detection, branch creation,
.erk/impl-context/ setup, and impl-context cleanup.

Usage:
    erk exec setup-impl                              # Auto-detect from .erk/impl-context/ or branch
    erk exec setup-impl --issue 2521                 # Set up from issue #2521
    erk exec setup-impl --file ./my-plan.md          # Set up from local file

Output:
    JSON with setup result including plan metadata and related docs.

Exit Codes:
    0: Success
    1: Error (plan not found, git operation failed, etc.)

Examples:
    $ erk exec setup-impl --issue 2521
    {"success": true, "pr_number": 2521, "source": "issue_arg", ...}

    $ erk exec setup-impl
    {"success": true, "pr_number": 2521, "source": "branch_detection", ...}

    $ erk exec setup-impl
    {"success": false, "error": "no_plan_found", ...}
"""

import json
import re
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.detect_plan_from_branch import _detect_plan_from_branch_impl
from erk.cli.commands.exec.scripts.impl_init import _extract_related_docs, _validate_impl_folder
from erk_shared.context.helpers import (
    require_branch_manager,
    require_cwd,
    require_git,
    require_github,
    require_repo_root,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_folder import create_impl_folder, read_plan_ref, resolve_impl_dir


def _run_impl_init(ctx: click.Context) -> dict[str, object]:
    """Run impl-init validation and return the result.

    Args:
        ctx: Click context for dependency injection.

    Returns:
        Dict with 'valid' key and plan metadata.

    Raises:
        SystemExit: If validation fails.
    """
    impl_dir = _validate_impl_folder(ctx)
    plan_ref = read_plan_ref(impl_dir)
    has_plan_tracking = plan_ref is not None
    if plan_ref is not None:
        plan_number: int | None = int(plan_ref.pr_id)
    else:
        plan_number = None
    plan_content = (impl_dir / "plan.md").read_text(encoding="utf-8")
    related_docs = _extract_related_docs(plan_content)

    result: dict[str, object] = {
        "valid": True,
        "has_plan_tracking": has_plan_tracking,
        "related_docs": related_docs,
    }
    if plan_number is not None:
        result["pr_number"] = plan_number
    return result


def _setup_from_file(
    ctx: click.Context,
    *,
    file_path: Path,
) -> dict[str, object]:
    """Set up implementation from a local markdown file.

    Creates a feature branch and .erk/impl-context/ folder from the file content.

    Args:
        ctx: Click context.
        file_path: Path to the markdown file.

    Returns:
        Setup result dict.
    """
    cwd = require_cwd(ctx)
    branch_manager = require_branch_manager(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    if not file_path.exists():
        return {
            "success": False,
            "error": "file_not_found",
            "message": f"File not found: {file_path}",
        }

    plan_content = file_path.read_text(encoding="utf-8")

    # Extract title from first heading
    title_match = re.search(r"^#\s+(.+)$", plan_content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "implementation"

    # Generate branch name from title
    branch_name = re.sub(r"[^a-z0-9-]", "-", title.lower())
    branch_name = re.sub(r"-+", "-", branch_name).strip("-")[:30]
    if not branch_name:
        branch_name = "implementation"

    # Get current branch for stacking
    current_branch = git.branch.get_current_branch(cwd)
    if current_branch is None:
        return {
            "success": False,
            "error": "detached_head",
            "message": "Cannot set up from detached HEAD",
        }

    # Create branch
    branch_manager.create_branch(repo_root, branch_name, current_branch)
    branch_manager.checkout_branch(cwd, branch_name)

    # Create impl folder
    create_impl_folder(
        worktree_path=cwd, plan_content=plan_content, branch_name=branch_name, overwrite=True
    )

    related_docs = _extract_related_docs(plan_content)

    return {
        "success": True,
        "source": "file",
        "branch": branch_name,
        "has_plan_tracking": False,
        "related_docs": related_docs,
    }


@click.command(name="setup-impl")
@click.option("--issue", "pr_number", type=int, default=None, help="PR number to set up from")
@click.option(
    "--file",
    "file_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Markdown file to set up from",
)
@click.pass_context
def setup_impl(ctx: click.Context, pr_number: int | None, file_path: Path | None) -> None:
    """Consolidated implementation setup.

    Handles all setup paths for plan-implement:
    1. --issue: Set up from a GitHub issue/PR
    2. --file: Set up from a local markdown file
    3. (no args): Auto-detect from .erk/impl-context/ or branch, or fail

    Runs impl-init validation, cleanup of .erk/impl-context/,
    and outputs plan metadata for the agent.
    """
    cwd = require_cwd(ctx)

    # Path 1: --issue provided
    if pr_number is not None:
        _handle_issue_setup(ctx, pr_number=pr_number)
        return

    # Path 2: --file provided
    if file_path is not None:
        result = _setup_from_file(ctx, file_path=file_path)
        if not result.get("success", False):
            click.echo(json.dumps(result), err=True)
            raise SystemExit(1)

        # Run impl-init for validation
        init_result = _run_impl_init(ctx)
        result["related_docs"] = init_result.get("related_docs", {"skills": [], "docs": []})
        click.echo(json.dumps(result))
        return

    # Path 3: Auto-detect
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    current_branch = git.branch.get_current_branch(cwd)

    # 3a: Check if impl already exists and is valid
    impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
    if impl_dir is not None:
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None:
            # Has plan tracking - sync with remote
            if plan_ref.pr_id.isdigit():
                plan_id: int | None = int(plan_ref.pr_id)
            else:
                plan_id = None
            if plan_id is not None:
                _handle_issue_setup(ctx, pr_number=plan_id)
                return

        # File-based plan (no tracking) - just validate
        if (impl_dir / "plan.md").exists():
            init_result = _run_impl_init(ctx)
            click.echo(
                json.dumps(
                    {
                        "success": True,
                        "source": "existing_impl",
                        "has_plan_tracking": False,
                        **init_result,
                    }
                )
            )
            return

    # 3b: Detect from branch

    def pr_lookup() -> int | None:
        if current_branch is None:
            return None
        pr_result = github.get_pr_for_branch(repo_root, current_branch)
        if isinstance(pr_result, PRNotFound):
            return None
        return pr_result.number

    detection = _detect_plan_from_branch_impl(
        current_branch=current_branch,
        pr_lookup=pr_lookup,
    )

    if detection.get("found"):
        detected_number = detection["pr_number"]
        if isinstance(detected_number, int):
            click.echo(f"Auto-detected PR #{detected_number} from branch", err=True)
            _handle_issue_setup(ctx, pr_number=detected_number)
            return

    # 3c: No PR found
    click.echo(
        json.dumps(
            {
                "success": False,
                "error": "no_plan_found",
                "message": "No PR found. Provide --issue, --file, or run from a PR branch.",
            }
        )
    )
    raise SystemExit(1)


def _handle_issue_setup(ctx: click.Context, *, pr_number: int) -> None:
    """Handle setup from a plan number (shared by explicit --issue and auto-detect).

    Delegates to setup-impl-from-pr, runs impl-init, runs cleanup,
    and outputs the combined result.

    Args:
        ctx: Click context.
        pr_number: The plan/PR number to set up from.
    """
    from erk.cli.commands.exec.scripts.setup_impl_from_pr import setup_impl_from_pr

    # Invoke setup-impl-from-pr as a sub-command
    runner_ctx = click.Context(setup_impl_from_pr, parent=ctx, info_name="setup-impl-from-pr")
    runner_ctx.obj = ctx.obj

    # Run setup-impl-from-pr
    ctx.invoke(
        setup_impl_from_pr,
        pr_number=pr_number,
        session_id=None,
        no_impl=False,
    )

    # Run impl-init for validation and metadata
    try:
        init_result = _run_impl_init(ctx)
    except SystemExit:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "impl_init_failed",
                    "message": "Implementation setup succeeded but init validation failed.",
                }
            )
        )
        raise SystemExit(1) from None

    # Output combined result
    click.echo(
        json.dumps(
            {
                "success": True,
                "source": "issue",
                "pr_number": pr_number,
                "has_plan_tracking": True,
                **init_result,
            }
        )
    )
