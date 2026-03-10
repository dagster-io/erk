"""Reset a plan branch to pre-implementation state for retry.

When implementation fails on a plan PR, the branch is left with partial
implementation commits and cleaned-up impl-context. This command resets
the branch to its merge-base with the PR's base branch, force-pushes
the reset, and resets lifecycle_stage to "planned".

Usage:
    erk exec impl-reset [--plan-number <N>]

If --plan-number is omitted, auto-detects from the current branch.

Output:
    JSON with success status and reset details.
    Always exits with code 0 (graceful degradation for || true pattern).

Examples:
    $ erk exec impl-reset
    {"success": true, "plan_number": 123, "reset_to": "abc123", "lifecycle_stage": "planned"}

    $ erk exec impl-reset --plan-number 456
    {"success": true, "plan_number": 456, "reset_to": "def789", "lifecycle_stage": "planned"}
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.metadata.core import render_erk_issue_event


@dataclass(frozen=True)
class ResetSuccess:
    """Success response for impl-reset command."""

    success: bool
    plan_number: int
    reset_to: str
    lifecycle_stage: str


@dataclass(frozen=True)
class ResetError:
    """Error response for impl-reset command."""

    success: bool
    error_type: str
    message: str


@dataclass(frozen=True)
class ResetNoOp:
    """No-op response when branch is already clean."""

    success: bool
    plan_number: int
    message: str


def _output_error(error_type: str, message: str) -> None:
    """Output error JSON and exit gracefully."""
    result = ResetError(success=False, error_type=error_type, message=message)
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


def _reset_branch(ctx: click.Context, plan_number_arg: int | None) -> None:
    """Core reset logic for impl-reset command.

    Steps:
    1. Detect plan PR from current branch (or use --plan-number)
    2. Get base_ref_name from plan metadata
    3. Fetch origin to ensure up-to-date refs
    4. Get merge-base between origin/<base_ref> and HEAD
    5. Check if branch has commits beyond merge-base (no-op if clean)
    6. git reset --hard to merge-base
    7. Force-push the reset
    8. Reset lifecycle_stage to "planned" on the PR
    """
    # Get context dependencies
    try:
        cwd = require_cwd(ctx)
        git = require_git(ctx)
        repo_root = require_repo_root(ctx)
        backend = require_plan_backend(ctx)
    except SystemExit:
        _output_error("context-not-initialized", "Context not initialized")
        return

    # Get current branch
    current_branch = git.branch.get_current_branch(cwd)
    if current_branch is None:
        _output_error("no-branch", "Not on a branch (detached HEAD)")
        return

    # Resolve plan number
    if plan_number_arg is not None:
        plan_number = plan_number_arg
    else:
        plan_id = backend.resolve_plan_id_for_branch(repo_root, current_branch)
        if plan_id is None:
            _output_error(
                "no-plan-found",
                f"Could not detect plan PR for branch '{current_branch}'",
            )
            return
        plan_number = int(plan_id)

    # Get plan to find base_ref_name
    from erk_shared.plan_store.types import PlanNotFound

    plan_result = backend.get_plan(repo_root, str(plan_number))
    if isinstance(plan_result, PlanNotFound):
        _output_error("plan-not-found", f"Plan #{plan_number} not found")
        return

    # Extract base_ref_name from plan metadata
    base_ref_raw = plan_result.metadata.get("base_ref_name")
    base_ref = base_ref_raw if isinstance(base_ref_raw, str) else "master"

    # Fetch origin to ensure up-to-date refs
    git.remote.fetch_branch(repo_root, "origin", base_ref)

    # Get merge-base
    merge_base = git.analysis.get_merge_base(repo_root, f"origin/{base_ref}", "HEAD")
    if merge_base is None:
        _output_error(
            "merge-base-failed",
            f"Could not compute merge-base between origin/{base_ref} and HEAD",
        )
        return

    # Check if branch has commits beyond merge-base
    commits_ahead = git.analysis.count_commits_ahead(cwd, f"origin/{base_ref}")
    if commits_ahead == 0:
        result = ResetNoOp(
            success=True,
            plan_number=plan_number,
            message="Branch is already at merge-base, no reset needed",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Reset branch to merge-base
    git.branch.reset_hard(cwd, merge_base)

    # Force-push the reset
    push_result = git.remote.push_to_remote(
        cwd, "origin", current_branch, set_upstream=False, force=True
    )
    if isinstance(push_result, PushError):
        _output_error("push-failed", f"Force push failed: {push_result.message}")
        return

    # Reset lifecycle_stage to "planned"
    reset_comment = render_erk_issue_event(
        title="\U0001f504 Branch reset for retry",
        metadata=None,
        description=f"Branch reset to `{merge_base[:8]}` (merge-base with `{base_ref}`).",
    )

    backend.post_event(
        repo_root,
        str(plan_number),
        metadata={"lifecycle_stage": "planned"},
        comment=reset_comment,
    )

    result = ResetSuccess(
        success=True,
        plan_number=plan_number,
        reset_to=merge_base,
        lifecycle_stage="planned",
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


@click.command(name="impl-reset")
@click.option(
    "--plan-number",
    type=int,
    default=None,
    help="Plan number to reset. Auto-detected from current branch if omitted.",
)
@click.pass_context
def impl_reset(ctx: click.Context, plan_number: int | None) -> None:
    """Reset a plan branch to pre-implementation state for retry.

    Resets the branch to its merge-base with the PR's base branch,
    force-pushes the reset, and sets lifecycle_stage to "planned".

    If --plan-number is omitted, auto-detects from the current branch.

    Always exits with code 0 for graceful degradation (|| true pattern).
    """
    _reset_branch(ctx, plan_number)
