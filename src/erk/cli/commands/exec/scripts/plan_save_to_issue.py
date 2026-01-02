"""Extract plan from ~/.claude/plans/ and create GitHub issue in one operation.

Usage:
    erk exec plan-save-to-issue [OPTIONS]

This command combines plan extraction and issue creation:
1. Extract plan from specified file, session-scoped lookup, or latest from ~/.claude/plans/
2. Create GitHub issue with plan content

Options:
    --plan-file PATH: Use specific plan file (highest priority)
    --session-id ID: Use session-scoped lookup to find plan by slug
    (neither): Fall back to most recent plan by modification time

Output:
    --format json (default): {"success": true, "issue_number": N, ...}
    --format display: Formatted text ready for display

Exit Codes:
    0: Success - plan extracted and issue created
    1: Error - no plan found, gh failure, etc.
"""

import json
from pathlib import Path

import click
import frontmatter
import yaml

from erk_shared.context.helpers import (
    get_repo_identifier,
    require_cwd,
    require_local_config,
    require_repo_root,
    require_session_store,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.extraction.local_plans import extract_slugs_from_session, get_plans_dir
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.output.next_steps import format_next_steps_plain
from erk_shared.scratch.plan_snapshots import snapshot_plan_for_session
from erk_shared.scratch.scratch import get_scratch_dir


def validate_plan_frontmatter(plan_content: str) -> None:
    """Validate plan has required frontmatter steps.

    Args:
        plan_content: The plan content to validate.

    Raises:
        click.ClickException: If frontmatter is missing, invalid, or steps array is empty.
    """
    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(plan_content)
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML frontmatter: {e}") from None

    if "steps" not in post.metadata:
        raise click.ClickException(
            "Plan missing required 'steps' in frontmatter.\n"
            "Add steps to the plan file before saving:\n\n"
            "---\n"
            "steps:\n"
            '  - name: "First step"\n'
            '  - name: "Second step"\n'
            "---"
        )

    steps = post.metadata["steps"]
    if not isinstance(steps, list):
        raise click.ClickException(f"'steps' must be a list, got {type(steps).__name__}")

    if len(steps) == 0:
        raise click.ClickException("Plan has empty 'steps' array. Add implementation steps.")

    # Validate each step is a dict with 'name' key
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise click.ClickException(
                f"Step {i + 1} must be a dictionary with 'name' key, got {type(step).__name__}.\n"
                "Use format:\n"
                "steps:\n"
                '  - name: "Step description"'
            )
        if "name" not in step:
            raise click.ClickException(
                f"Step {i + 1} missing required 'name' key.\n"
                "Use format:\n"
                "steps:\n"
                '  - name: "Step description"'
            )


def _create_plan_saved_marker(session_id: str, repo_root: Path) -> None:
    """Create marker file to indicate plan was saved to GitHub.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    marker_file.write_text(
        "Created by: exit-plan-mode-hook (via /erk:plan-save)\n"
        "Trigger: Plan was successfully saved to GitHub\n"
        "Effect: Next ExitPlanMode call will be BLOCKED (remain in plan mode, session complete)\n"
        "Lifecycle: Deleted after being read by next hook invocation\n",
        encoding="utf-8",
    )


@click.command(name="plan-save-to-issue")
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
    help="Session ID for scoped plan lookup (uses slug from session logs)",
)
@click.pass_context
def plan_save_to_issue(
    ctx: click.Context, output_format: str, plan_file: Path | None, session_id: str | None
) -> None:
    """Extract plan from ~/.claude/plans/ and create GitHub issue.

    Combines plan extraction and issue creation in a single operation.
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    session_store = require_session_store(ctx)

    # session_id comes from --session-id CLI option (or None if not provided)
    effective_session_id = session_id

    # Step 1: Extract plan (priority: plan_file > session_id > most recent)
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = session_store.get_latest_plan(cwd, session_id=effective_session_id)

    if not plan:
        if output_format == "display":
            click.echo("Error: No plan found in ~/.claude/plans/", err=True)
            click.echo("\nTo fix:", err=True)
            click.echo("1. Create a plan (enter Plan mode if needed)", err=True)
            click.echo("2. Exit Plan mode using ExitPlanMode tool", err=True)
            click.echo("3. Run this command again", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"}))
        raise SystemExit(1)

    # Validate frontmatter before saving
    try:
        validate_plan_frontmatter(plan)
    except click.ClickException as e:
        if output_format == "display":
            click.echo(f"Error: {e.message}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": e.message}))
        raise SystemExit(1) from None

    # Determine source_repo for cross-repo plans
    # When plans_repo is configured, plans are stored in a separate repo
    # and source_repo records where implementation will happen
    source_repo: str | None = None
    config = require_local_config(ctx)
    if config.plans_repo is not None:
        source_repo = get_repo_identifier(ctx)

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=plan,
        title=None,
        plan_type=None,
        extra_labels=None,
        title_suffix=None,
        source_plan_issues=None,
        extraction_session_ids=None,
        source_repo=source_repo,
        objective_issue=None,
    )

    if not result.success:
        if result.issue_number is not None:
            # Partial success - issue created but comment failed
            if output_format == "display":
                click.echo(f"Warning: {result.error}", err=True)
                click.echo(f"Please manually add plan content to: {result.issue_url}", err=True)
            else:
                click.echo(
                    json.dumps(
                        {
                            "success": False,
                            "error": result.error,
                            "issue_number": result.issue_number,
                            "issue_url": result.issue_url,
                        }
                    )
                )
        else:
            if output_format == "display":
                click.echo(f"Error: {result.error}", err=True)
            else:
                click.echo(json.dumps({"success": False, "error": result.error}))
        raise SystemExit(1)

    # DISABLED: Session context embedding is temporarily disabled while rethinking extraction plans
    # To re-enable, uncomment the following block and restore imports:
    #   from erk_shared.context.helpers import require_git
    #   from erk_shared.extraction.session_context import collect_session_context
    #   from erk_shared.github.metadata import render_session_content_blocks
    #
    #   git = require_git(ctx)
    #   session_result = collect_session_context(
    #       git=git,
    #       cwd=cwd,
    #       session_store=session_store,
    #       current_session_id=effective_session_id,
    #       min_size=1024,
    #       limit=20,
    #   )
    #
    #   if session_result is not None and result.issue_number is not None:
    #       # Render and post as comments
    #       session_label = session_result.branch_context.current_branch or "planning-session"
    #       content_blocks = render_session_content_blocks(
    #           content=session_result.combined_xml,
    #           session_label=session_label,
    #           extraction_hints=["Planning session context for downstream analysis"],
    #       )
    #
    #       # Post each block as a comment (failures are non-blocking)
    #       for block in content_blocks:
    #           try:
    #               github.add_comment(repo_root, result.issue_number, block)
    #               session_context_chunks += 1
    #           except RuntimeError:
    #               # Session context is supplementary - don't fail the command
    #               pass
    #
    #       session_ids = session_result.session_ids

    # Output JSON still includes these for backwards compatibility
    session_context_chunks = 0
    session_ids: list[str] = []

    # Step 9: Create marker file to indicate plan was saved
    snapshot_result = None
    if effective_session_id:
        _create_plan_saved_marker(effective_session_id, repo_root)

        # Step 9.1: Snapshot the plan file to session-scoped storage
        # Determine plan file path
        if plan_file:
            snapshot_path = plan_file
        else:
            # Look up slug from session to find plan file
            slugs = extract_slugs_from_session(effective_session_id, cwd_hint=str(cwd))
            if slugs:
                snapshot_path = get_plans_dir() / f"{slugs[-1]}.md"
            else:
                snapshot_path = None

        if snapshot_path is not None and snapshot_path.exists():
            snapshot_result = snapshot_plan_for_session(
                session_id=effective_session_id,
                plan_file_path=snapshot_path,
                cwd_hint=str(cwd),
                repo_root=repo_root,
            )

    # Step 10: Output success
    # Detect enrichment status for informational output
    is_enriched = "## Enrichment Details" in plan

    # At this point result.success is True, so issue_number must be set
    # Guard for type narrowing
    if result.issue_number is None:
        raise RuntimeError("Unexpected: issue_number is None after successful create_plan_issue")

    if output_format == "display":
        click.echo(f"Plan saved to GitHub issue #{result.issue_number}")
        click.echo(f"Title: {result.title}")
        click.echo(f"URL: {result.issue_url}")
        click.echo(f"Enrichment: {'Yes' if is_enriched else 'No'}")
        if session_context_chunks > 0:
            click.echo(f"Session context: {session_context_chunks} chunks")
        if snapshot_result is not None:
            click.echo(f"Archived: {snapshot_result.snapshot_dir}")
        click.echo()
        click.echo(format_next_steps_plain(result.issue_number))
    else:
        output_data = {
            "success": True,
            "issue_number": result.issue_number,
            "issue_url": result.issue_url,
            "title": result.title,
            "enriched": is_enriched,
            "session_context_chunks": session_context_chunks,
            "session_ids": session_ids,
        }
        if snapshot_result is not None:
            output_data["archived_to"] = str(snapshot_result.snapshot_dir)
        click.echo(json.dumps(output_data))
