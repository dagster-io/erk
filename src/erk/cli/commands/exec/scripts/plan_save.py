"""Backend-aware plan save: dispatches to issue or draft-PR based on constant.

Usage:
    erk exec plan-save [OPTIONS]

When ERK_PLAN_BACKEND is "draft_pr", creates a draft PR with the plan.
Otherwise delegates to the existing plan-save-to-issue logic (default).

Options:
    --format json|display: Output format (default: json)
    --plan-file PATH: Use specific plan file (highest priority)
    --session-id ID: Session ID for scoped plan lookup
    --objective-issue INT: Link plan to parent objective
    --plan-type standard|learn: Plan type (default: standard)
    --learned-from-issue INT: Parent plan issue (for learn plans)
    --created-from-workflow-run-url URL: Workflow run URL

Exit Codes:
    0: Success
    1: Error
    2: Validation failed
"""

import json
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.plan_save_to_issue import (
    plan_save_to_issue,
)
from erk.cli.commands.exec.scripts.validate_plan_content import _validate_plan_content
from erk_shared.context.helpers import (
    get_repo_identifier,
    require_branch_manager,
    require_claude_installation,
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_local_config,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.claude_installation.abc import ClaudeInstallation
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.gateway.time.real import RealTime
from erk_shared.naming import generate_draft_pr_branch_name
from erk_shared.plan_store import get_plan_backend
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.plan_content import extract_title_from_plan, resolve_plan_content
from erk_shared.scratch.plan_snapshots import PlanSnapshot, snapshot_plan_for_session
from erk_shared.scratch.session_markers import (
    create_plan_saved_issue_marker,
    create_plan_saved_marker,
    get_existing_saved_issue,
)


def _get_snapshot_result(
    *,
    session_id: str,
    plan_file: Path | None,
    cwd: Path,
    claude_installation: ClaudeInstallation,
    repo_root: Path,
) -> PlanSnapshot | None:
    """Archive the plan file to session-scoped scratch storage.

    Plan snapshots preserve the original plan content at save time, creating
    an immutable record tied to the session. This enables deduplication
    (detecting if a session already saved a plan) and provides an audit trail
    (what was the plan content when it was saved).

    Args:
        session_id: Claude session ID
        plan_file: Explicit plan file path (highest priority)
        cwd: Current working directory
        claude_installation: ClaudeInstallation gateway for plan discovery
        repo_root: Repository root for scratch directory

    Returns:
        PlanSnapshot with archive path, or None if no plan file found.
    """
    if plan_file is not None:
        snapshot_path = plan_file
    else:
        snapshot_path = claude_installation.find_plan_for_session(cwd, session_id)

    if snapshot_path is None or not snapshot_path.exists():
        return None

    return snapshot_plan_for_session(
        session_id=session_id,
        plan_file_path=snapshot_path,
        project_cwd=cwd,
        claude_installation=claude_installation,
        repo_root=repo_root,
    )


def _save_as_draft_pr(
    ctx: click.Context,
    *,
    plan_content: str,
    session_id: str | None,
    objective_issue: int | None,
    plan_type: str | None,
    output_format: str,
    plan_file: Path | None,
) -> None:
    """Save plan as a draft PR.

    Creates a branch, pushes it, then creates a draft PR with plan content.

    Args:
        ctx: Click context
        plan_content: Validated plan content
        session_id: Session ID for markers
        objective_issue: Optional objective issue number
        plan_type: Plan type (standard or learn)
        output_format: Output format (json or display)
        plan_file: Original plan file path (for snapshot)
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    config = require_local_config(ctx)
    claude_installation = require_claude_installation(ctx)

    title = extract_title_from_plan(plan_content)

    # Generate branch name
    now = require_time(ctx).now()
    branch_name = generate_draft_pr_branch_name(
        title,
        now,
        objective_id=objective_issue,
    )

    # Create branch with Graphite tracking (handles both creation and stack metadata)
    branch_manager = require_branch_manager(ctx)
    current_branch = git.branch.get_current_branch(cwd)
    start_point = current_branch if current_branch is not None else "HEAD"
    create_result = branch_manager.create_branch(repo_root, branch_name, start_point)
    if isinstance(create_result, BranchAlreadyExists):
        click.echo(f"Error: {create_result.message}", err=True)
        raise SystemExit(1) from None

    # Detect trunk for PR base metadata
    trunk = git.branch.detect_trunk_branch(cwd)

    # Temporarily checkout plan branch to commit plan file.
    # Since the plan branch was created from the same commit as the current branch,
    # checkout won't conflict with uncommitted work.
    git.branch.checkout_branch(cwd, branch_name)
    try:
        branch_data_dir = repo_root / ".erk" / "branch-data"
        branch_data_dir.mkdir(parents=True, exist_ok=True)
        plan_file_path = branch_data_dir / "plan.md"
        plan_file_path.write_text(plan_content, encoding="utf-8")

        # Write ref.json with plan reference metadata
        ref_data: dict[str, str | int | None] = {
            "provider": "github-draft-pr",
            "url": None,  # Not yet known; populated after PR creation
        }
        if objective_issue is not None:
            ref_data["objective_id"] = objective_issue
        ref_file_path = branch_data_dir / "ref.json"
        ref_file_path.write_text(json.dumps(ref_data, indent=2), encoding="utf-8")

        git.commit.stage_files(repo_root, [".erk/branch-data/plan.md", ".erk/branch-data/ref.json"])
        git.commit.commit(repo_root, f"Add plan: {title}")
        git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)
    finally:
        git.branch.checkout_branch(cwd, start_point)

    # Build metadata
    metadata: dict[str, object] = {"branch_name": branch_name, "trunk_branch": trunk}

    if config.plans_repo is not None:
        metadata["source_repo"] = get_repo_identifier(ctx)

    if objective_issue is not None:
        metadata["objective_issue"] = objective_issue

    if session_id is not None:
        metadata["created_from_session"] = session_id

    # Build labels
    labels = ["erk-plan"]
    if plan_type == "learn":
        labels.append("erk-learn")

    # Create draft PR via backend
    backend = DraftPRPlanBackend(github, github_issues, time=RealTime())
    result = backend.create_plan(
        repo_root=repo_root,
        title=title,
        content=plan_content,
        labels=tuple(labels),
        metadata=metadata,
    )

    if not result.plan_id.isdigit():
        msg = f"Expected numeric plan_id from draft PR creation, got: {result.plan_id!r}"
        raise RuntimeError(msg)
    plan_number = int(result.plan_id)

    # Create markers and snapshot
    snapshot_result: PlanSnapshot | None = None
    if session_id is not None:
        create_plan_saved_marker(session_id, repo_root)
        create_plan_saved_issue_marker(session_id, repo_root, plan_number)

        snapshot_result = _get_snapshot_result(
            session_id=session_id,
            plan_file=plan_file,
            cwd=cwd,
            claude_installation=claude_installation,
            repo_root=repo_root,
        )

    # Output
    if output_format == "display":
        click.echo(f"Plan saved as draft PR #{plan_number}")
        click.echo(f"Title: {title}")
        click.echo(f"URL: {result.url}")
        click.echo(f"Branch: {branch_name}")
        if snapshot_result is not None:
            click.echo(f"Archived: {snapshot_result.snapshot_dir}")
    else:
        output_data: dict[str, str | int | bool | None] = {
            "success": True,
            "issue_number": plan_number,
            "issue_url": result.url,
            "title": title,
            "branch_name": branch_name,
            "plan_backend": "draft_pr",
        }
        if snapshot_result is not None:
            output_data["archived_to"] = str(snapshot_result.snapshot_dir)
        click.echo(json.dumps(output_data))


def _save_plan_via_draft_pr(
    ctx: click.Context,
    *,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
    objective_issue: int | None,
    plan_type: str | None,
) -> None:
    """Handle draft-PR backend: dedup check, plan extraction, validation, and save.

    Args:
        ctx: Click context
        output_format: Output format (json or display)
        plan_file: Explicit plan file path (highest priority)
        session_id: Session ID for dedup and markers
        objective_issue: Optional objective issue number
        plan_type: Plan type (standard or learn)
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Session deduplication check
    if session_id is not None:
        existing_issue = get_existing_saved_issue(session_id, repo_root)
        if existing_issue is not None:
            if output_format == "display":
                click.echo(
                    f"This session already saved plan #{existing_issue}. "
                    "Skipping duplicate creation.",
                    err=True,
                )
            else:
                click.echo(
                    json.dumps(
                        {
                            "success": True,
                            "issue_number": existing_issue,
                            "skipped_duplicate": True,
                            "message": f"Session already saved plan #{existing_issue}",
                        }
                    )
                )
            return

    # Extract plan content (same priority as plan-save-to-issue)
    plan = resolve_plan_content(
        plan_file=plan_file,
        session_id=session_id,
        repo_root=repo_root,
        claude_installation=claude_installation,
        cwd=cwd,
    )

    if not plan:
        if output_format == "display":
            click.echo("Error: No plan found in ~/.claude/plans/", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"}))
        raise SystemExit(1)

    # Validate plan content
    valid, error, details = _validate_plan_content(plan)
    if not valid:
        if output_format == "display":
            click.echo(f"Error: Plan validation failed: {error}", err=True)
        else:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Plan validation failed: {error}",
                        "error_type": "validation_failed",
                        "details": details,
                    }
                )
            )
        raise SystemExit(2)

    _save_as_draft_pr(
        ctx,
        plan_content=plan,
        session_id=session_id,
        objective_issue=objective_issue,
        plan_type=plan_type,
        output_format=output_format,
        plan_file=plan_file,
    )


@click.command(name="plan-save")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to specific plan file (highest priority)",
)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for scoped plan lookup",
)
@click.option(
    "--objective-issue",
    type=int,
    default=None,
    help="Link plan to parent objective issue number",
)
@click.option(
    "--plan-type",
    type=click.Choice(["standard", "learn"]),
    default=None,
    help="Plan type: standard (default) or learn",
)
@click.option(
    "--learned-from-issue",
    type=int,
    default=None,
    help="Parent plan issue number (for learn plans)",
)
@click.option(
    "--created-from-workflow-run-url",
    default=None,
    help="GitHub Actions workflow run URL",
)
@click.pass_context
def plan_save(
    ctx: click.Context,
    *,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
    objective_issue: int | None,
    plan_type: str | None,
    learned_from_issue: int | None,
    created_from_workflow_run_url: str | None,
) -> None:
    """Backend-aware plan save: dispatches to issue or draft-PR based on constant.

    When ERK_PLAN_BACKEND is "draft_pr", creates a draft PR.
    Otherwise delegates to plan-save-to-issue.
    """
    # PLAN_BACKEND_SPLIT: dispatches to issue-based save or draft-PR save based on ERK_PLAN_BACKEND
    # Default backend: delegate to issue-based save
    if get_plan_backend() != "draft_pr":
        ctx.invoke(
            plan_save_to_issue,
            output_format=output_format,
            plan_file=plan_file,
            session_id=session_id,
            objective_issue=objective_issue,
            plan_type=plan_type,
            learned_from_issue=learned_from_issue,
            created_from_workflow_run_url=created_from_workflow_run_url,
        )
        return

    _save_plan_via_draft_pr(
        ctx,
        output_format=output_format,
        plan_file=plan_file,
        session_id=session_id,
        objective_issue=objective_issue,
        plan_type=plan_type,
    )
