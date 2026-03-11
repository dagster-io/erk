"""Plan save: creates a draft PR with the plan content.

Usage:
    erk exec plan-save [OPTIONS]

Options:
    --format json|display: Output format (default: json)
    --plan-file PATH: Use specific plan file (highest priority)
    --session-id ID: Session ID for scoped plan lookup
    --plan-type standard|learn: Plan type (default: standard)
    --learned-from-issue INT: Parent plan (for learn plans)
    --created-from-workflow-run-url URL: Workflow run URL

Objective linking: use --objective to pass directly, or rely on
automatic linking via the objective-context session marker
(created by /erk:objective-plan). The --objective flag takes
precedence over the session marker.

Exit Codes:
    0: Success
    1: Error
    2: Validation failed
"""

import json
from pathlib import Path

import click

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
from erk_shared.naming import (
    InvalidPlanTitle,
    generate_planned_pr_branch_name,
    validate_plan_title,
)
from erk_shared.output.next_steps import format_plan_next_steps_plain
from erk_shared.plan_store.plan_content import extract_title_from_plan, resolve_plan_content
from erk_shared.plan_store.planned_pr import ManagedGitHubPrBackend
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_utils import get_title_tag_from_labels
from erk_shared.scratch.plan_snapshots import PlanSnapshot, snapshot_plan_for_session
from erk_shared.scratch.session_markers import (
    create_plan_saved_branch_marker,
    create_plan_saved_issue_marker,
    create_plan_saved_marker,
    get_existing_saved_branch,
    get_existing_saved_issue,
    read_objective_context_marker,
    read_roadmap_step_marker,
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


def _save_as_planned_pr(
    ctx: click.Context,
    *,
    plan_content: str,
    session_id: str | None,
    objective_issue: int | None,
    plan_type: str | None,
    output_format: str,
    plan_file: Path | None,
    learned_from_issue: int | None,
    created_from_workflow_run_url: str | None,
    branch_slug: str | None,
    node_ids: tuple[str, ...] | None,
    summary: str | None,
    session_xml_dir: Path | None,
    current_branch_flag: bool,
) -> None:
    """Save plan as a planned PR.

    Creates a branch, pushes it, then creates a planned PR with plan content.

    Args:
        ctx: Click context
        plan_content: Validated plan content
        session_id: Session ID for markers
        objective_issue: Optional objective issue number
        plan_type: Plan type (standard or learn)
        output_format: Output format (json or display)
        plan_file: Original plan file path (for snapshot)
        learned_from_issue: Parent plan number (for learn plans)
        created_from_workflow_run_url: GitHub Actions workflow run URL
        branch_slug: Pre-generated branch slug (skips LLM call when provided)
        node_ids: Objective roadmap node IDs to associate with this plan
        summary: AI-generated summary for the PR description (None coerced to empty string)
        session_xml_dir: Directory containing session XML files to embed in the PR diff
        current_branch_flag: When True, use the current branch directly
            instead of creating a new one.
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    config = require_local_config(ctx)
    claude_installation = require_claude_installation(ctx)

    title = extract_title_from_plan(plan_content)

    # Validate plan title before proceeding
    title_validation = validate_plan_title(title)
    if isinstance(title_validation, InvalidPlanTitle):
        if output_format == "display":
            click.echo(f"Error: {title_validation.message}", err=True)
        else:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Plan title validation failed: {title_validation.reason}",
                        "error_type": "validation_failed",
                        "agent_guidance": title_validation.message,
                    }
                )
            )
        raise SystemExit(2)

    trunk = git.branch.detect_trunk_branch(repo_root)
    branch_manager = require_branch_manager(ctx)

    if current_branch_flag:
        # Use the current branch directly — no new branch creation
        current_branch = git.branch.get_current_branch(repo_root)
        if current_branch is None:
            click.echo("Error: --current-branch requires a checked-out branch.", err=True)
            raise SystemExit(1)
        branch_name = current_branch
        base_branch = trunk
    else:
        if not branch_slug:
            click.echo(
                "Error: --branch-slug is required. "
                "Generate a slug in the calling skill (e.g., plan-save.md Step 1.5) "
                "and pass it via --branch-slug.",
                err=True,
            )
            raise SystemExit(1)
        slug = branch_slug
        now = require_time(ctx).now()
        branch_name = generate_planned_pr_branch_name(
            slug,
            now,
            objective_id=objective_issue,
        )

        # Determine base branch: use current branch if on a feature branch, otherwise trunk
        current_branch = git.branch.get_current_branch(repo_root)

        if (
            current_branch is not None
            and current_branch != trunk
            and not current_branch.startswith("learn/")
            and git.branch.branch_exists_on_remote(repo_root, "origin", current_branch)
        ):
            # Stack plan branch on current feature branch for natural Graphite stacking
            base_branch = current_branch
            create_result = branch_manager.create_branch(repo_root, branch_name, current_branch)
        else:
            # On trunk or detached HEAD: create from origin/trunk
            base_branch = trunk
            git.remote.fetch_branch(repo_root, "origin", trunk)
            create_result = branch_manager.create_branch(repo_root, branch_name, f"origin/{trunk}")
        if isinstance(create_result, BranchAlreadyExists):
            click.echo(f"Error: {create_result.message}", err=True)
            raise SystemExit(1) from None

    # Build ref.json data
    ref_data: dict[str, str | int | list[str] | None] = {
        "provider": "github-draft-pr",
        "title": title,
    }
    if objective_issue is not None:
        ref_data["objective_id"] = objective_issue
    if node_ids is not None:
        ref_data["node_ids"] = list(node_ids)

    # Commit plan files directly to branch (no checkout needed).
    # Uses git plumbing to avoid race conditions when multiple sessions
    # share the same worktree.
    files: dict[str, str] = {
        f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
        f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
    }

    if session_xml_dir is not None:
        for xml_file in sorted(session_xml_dir.glob("*.xml")):
            if xml_file.is_file():
                files[f"{IMPL_CONTEXT_DIR}/sessions/{xml_file.name}"] = xml_file.read_text(
                    encoding="utf-8"
                )

    git.commit.commit_files_to_branch(
        repo_root,
        branch=branch_name,
        files=files,
        message=f"Add plan: {title}",
    )

    # Update Graphite tracking after plumbing commit advanced the branch
    # (create_branch tracked position A, but commit_files_to_branch moved to B)
    if not current_branch_flag:
        branch_manager.retrack_branch(repo_root, branch_name)

    # When saving on the current branch, the git plumbing commit advanced HEAD
    # but left the working tree and index unchanged. Write files to disk and
    # stage them so git status is clean.
    if current_branch_flag:
        for rel_path, content in files.items():
            abs_path = repo_root / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
        git.commit.stage_files(repo_root, list(files.keys()), force=True)

    git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)

    # Build metadata — base_ref_name sets the PR base ref
    metadata: dict[str, object] = {"branch_name": branch_name, "base_ref_name": base_branch}

    if config.github_repo is not None:
        metadata["source_repo"] = get_repo_identifier(ctx)

    if objective_issue is not None:
        metadata["objective_issue"] = objective_issue

    if session_id is not None:
        metadata["created_from_session"] = session_id

    if learned_from_issue is not None:
        metadata["learned_from_issue"] = learned_from_issue

    if created_from_workflow_run_url is not None:
        metadata["created_from_workflow_run_url"] = created_from_workflow_run_url

    # Build labels
    labels = ["erk-pr"]
    if plan_type == "learn":
        labels.append("erk-learn")

    # Prefix title with [erk-pr] or [erk-learn] for GitHub visibility
    title_tag = get_title_tag_from_labels(labels)
    prefixed_title = f"{title_tag} {title}"

    # Create draft PR via backend
    backend = ManagedGitHubPrBackend(github, github_issues, time=RealTime())
    result = backend.create_managed_pr(
        repo_root=repo_root,
        title=prefixed_title,
        content=plan_content,
        labels=tuple(labels),
        metadata=metadata,
        summary=summary or "",
    )

    if not result.pr_id.isdigit():
        msg = f"Expected numeric pr_id from planned PR creation, got: {result.pr_id!r}"
        raise RuntimeError(msg)
    pr_number = int(result.pr_id)

    # Create markers and snapshot
    snapshot_result: PlanSnapshot | None = None
    if session_id is not None:
        create_plan_saved_marker(session_id, repo_root, pr_number)
        create_plan_saved_issue_marker(session_id, repo_root, pr_number, title=title)
        create_plan_saved_branch_marker(session_id, repo_root, branch_name)

        snapshot_result = _get_snapshot_result(
            session_id=session_id,
            plan_file=plan_file,
            cwd=cwd,
            claude_installation=claude_installation,
            repo_root=repo_root,
        )

    # Output
    if output_format == "display":
        click.echo(f"PR saved as planned PR #{pr_number}")
        click.echo(f"Title: {prefixed_title}")
        click.echo(f"URL: {result.url}")
        click.echo(f"Branch: {branch_name}")
        if snapshot_result is not None:
            click.echo(f"Archived: {snapshot_result.snapshot_dir}")
        click.echo()
        click.echo(format_plan_next_steps_plain(pr_number, url=result.url))
    else:
        output_data: dict[str, str | int | bool | None] = {
            "success": True,
            "pr_number": pr_number,
            "pr_url": result.url,
            "title": prefixed_title,
            "branch_name": branch_name,
            "plan_backend": "planned_pr",
            "objective_issue": objective_issue,
        }
        if snapshot_result is not None:
            output_data["archived_to"] = str(snapshot_result.snapshot_dir)
        click.echo(json.dumps(output_data))


def _save_plan_via_planned_pr(
    ctx: click.Context,
    *,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
    plan_type: str | None,
    learned_from_issue: int | None,
    created_from_workflow_run_url: str | None,
    branch_slug: str | None,
    objective: int | None,
    summary: str | None,
    session_xml_dir: Path | None,
    current_branch_flag: bool,
) -> None:
    """Handle planned-PR backend: dedup check, plan extraction, validation, and save.

    Args:
        ctx: Click context
        output_format: Output format (json or display)
        plan_file: Explicit plan file path (highest priority)
        session_id: Session ID for dedup and markers
        plan_type: Plan type (standard or learn)
        learned_from_issue: Parent plan number (for learn plans)
        created_from_workflow_run_url: GitHub Actions workflow run URL
        branch_slug: Pre-generated branch slug (skips LLM call when provided)
        objective: Objective issue number from CLI flag (overrides session marker)
        summary: Optional AI-generated summary for the PR description
        session_xml_dir: Directory containing session XML files to embed in the PR diff
        current_branch_flag: When True, use current branch instead of creating a new one.
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # CLI flag takes precedence over marker
    objective_issue: int | None = objective
    node_ids: tuple[str, ...] | None = None
    if objective_issue is not None:
        click.echo(f"Linked to objective #{objective_issue} from --objective flag", err=True)
    elif session_id is not None:
        objective_issue = read_objective_context_marker(session_id, repo_root)
        if objective_issue is not None:
            click.echo(f"Linked to objective #{objective_issue} from session context", err=True)

    if session_id is not None:
        step_id = read_roadmap_step_marker(session_id, repo_root)
        if step_id is not None:
            node_ids = (step_id,)

    # Extract plan content before dedup so we can key dedup by title
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

    title = extract_title_from_plan(plan)

    # Session deduplication check (keyed by plan title)
    if session_id is not None:
        existing_issue = get_existing_saved_issue(session_id, repo_root, title=title)
        if existing_issue is not None:
            existing_branch = get_existing_saved_branch(session_id, repo_root)
            if output_format == "display":
                click.echo(
                    f"This session already saved PR #{existing_issue}. "
                    "Skipping duplicate creation.",
                    err=True,
                )
            else:
                dedup_response = {
                    "success": True,
                    "pr_number": existing_issue,
                    "skipped_duplicate": True,
                    "message": f"Session already saved PR #{existing_issue}",
                    "plan_backend": "planned_pr",
                }
                if existing_branch is not None:
                    dedup_response["branch_name"] = existing_branch
                click.echo(json.dumps(dedup_response))
            return

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

    _save_as_planned_pr(
        ctx,
        plan_content=plan,
        session_id=session_id,
        objective_issue=objective_issue,
        plan_type=plan_type,
        output_format=output_format,
        plan_file=plan_file,
        learned_from_issue=learned_from_issue,
        created_from_workflow_run_url=created_from_workflow_run_url,
        branch_slug=branch_slug,
        node_ids=node_ids,
        summary=summary,
        session_xml_dir=session_xml_dir,
        current_branch_flag=current_branch_flag,
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
    help="Path to specific PR file (highest priority)",
)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for scoped PR lookup",
)
@click.option(
    "--plan-type",
    type=click.Choice(["standard", "learn"]),
    default=None,
    help="PR type: standard (default) or learn",
)
@click.option(
    "--learned-from-issue",
    type=int,
    default=None,
    help="Parent PR number (for learn plans)",
)
@click.option(
    "--created-from-workflow-run-url",
    default=None,
    help="GitHub Actions workflow run URL",
)
@click.option(
    "--branch-slug",
    default=None,
    help="Pre-generated branch slug (skips LLM call when provided)",
)
@click.option(
    "--objective",
    type=int,
    default=None,
    help="Objective issue number (overrides session marker)",
)
@click.option(
    "--summary",
    default=None,
    help="AI-generated PR summary for PR description",
)
@click.option(
    "--session-xml-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory containing session XML files to embed in the PR diff",
)
@click.option(
    "--current-branch",
    "current_branch_flag",
    is_flag=True,
    default=False,
    help="Use the current branch directly instead of creating a new plnd/ branch",
)
@click.pass_context
def plan_save(
    ctx: click.Context,
    *,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
    plan_type: str | None,
    learned_from_issue: int | None,
    created_from_workflow_run_url: str | None,
    branch_slug: str | None,
    objective: int | None,
    summary: str | None,
    session_xml_dir: Path | None,
    current_branch_flag: bool,
) -> None:
    """Save plan as a draft PR."""
    _save_plan_via_planned_pr(
        ctx,
        output_format=output_format,
        plan_file=plan_file,
        session_id=session_id,
        plan_type=plan_type,
        learned_from_issue=learned_from_issue,
        created_from_workflow_run_url=created_from_workflow_run_url,
        branch_slug=branch_slug,
        objective=objective,
        summary=summary,
        session_xml_dir=session_xml_dir,
        current_branch_flag=current_branch_flag,
    )
