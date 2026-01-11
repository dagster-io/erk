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

from erk_shared.context.helpers import (
    get_repo_identifier,
    require_claude_installation,
    require_cwd,
    require_local_config,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.github.metadata.session import render_session_exchanges_block
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.learn.extraction.session_schema import extract_session_exchanges_from_jsonl
from erk_shared.output.next_steps import format_next_steps_plain
from erk_shared.scratch.plan_snapshots import snapshot_plan_for_session
from erk_shared.scratch.scratch import get_scratch_dir


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


def _create_plan_saved_issue_marker(session_id: str, repo_root: Path, issue_number: int) -> None:
    """Create marker file storing the issue number of the saved plan.

    This marker enables automatic plan updates - when user says "update plan",
    Claude can read this marker to find the issue number and invoke /local:plan-update.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        issue_number: The GitHub issue number where the plan was saved.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "plan-saved-issue.marker"
    marker_file.write_text(str(issue_number), encoding="utf-8")


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
    help="Plan type: standard (default) or learn (for documentation learning plans)",
)
@click.pass_context
def plan_save_to_issue(
    ctx: click.Context,
    *,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
    objective_issue: int | None,
    plan_type: str | None,
) -> None:
    """Extract plan from ~/.claude/plans/ and create GitHub issue.

    Combines plan extraction and issue creation in a single operation.
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # session_id comes from --session-id CLI option (or None if not provided)
    effective_session_id = session_id

    # Step 1: Extract plan (priority: plan_file > session_id > most recent)
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = claude_installation.get_latest_plan(cwd, session_id=effective_session_id)

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

    # Determine source_repo for cross-repo plans
    # When plans_repo is configured, plans are stored in a separate repo
    # and source_repo records where implementation will happen
    source_repo: str | None = None
    config = require_local_config(ctx)
    if config.plans_repo is not None:
        source_repo = get_repo_identifier(ctx)

    # Convert plan_type to extra_labels (erk-learn label indicates learn plans)
    extra_labels: list[str] | None = None
    if plan_type == "learn":
        extra_labels = ["erk-learn"]

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=plan,
        title=None,
        extra_labels=extra_labels,
        title_suffix=None,
        source_repo=source_repo,
        objective_issue=objective_issue,
        created_from_session=effective_session_id,
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

    # Step 9: Create marker files to indicate plan was saved
    snapshot_result = None
    if effective_session_id:
        _create_plan_saved_marker(effective_session_id, repo_root)

        # Step 9.0.1: Also store the issue number in a separate marker
        # This enables automatic plan updates - when user says "update plan",
        # Claude can read this marker to find the issue number
        if result.issue_number is not None:
            _create_plan_saved_issue_marker(effective_session_id, repo_root, result.issue_number)

        # Step 9.0.2: Upload session exchanges as a metadata block comment
        # Each exchange pairs a user prompt with the preceding assistant message
        # for context (e.g., understanding what "yes" was responding to)
        if result.issue_number is not None:
            session_content = claude_installation.read_session(
                cwd,
                effective_session_id,
                include_agents=False,
            )
            if session_content is not None:
                exchanges = extract_session_exchanges_from_jsonl(
                    session_content.main_content,
                    max_exchanges=20,
                    max_text_length=500,
                )
                if exchanges:
                    # Convert SessionExchange objects to tuples for render function
                    exchange_tuples = [(ex.preceding_assistant, ex.user_prompt) for ex in exchanges]
                    exchanges_block = render_session_exchanges_block(
                        exchange_tuples,
                        max_text_display_length=500,
                    )
                    github.add_comment(repo_root, result.issue_number, exchanges_block)

        # Step 9.1: Snapshot the plan file to session-scoped storage
        # Determine plan file path
        if plan_file:
            snapshot_path = plan_file
        else:
            # Look up slug from session to find plan file
            snapshot_path = claude_installation.find_plan_for_session(cwd, effective_session_id)

        if snapshot_path is not None and snapshot_path.exists():
            snapshot_result = snapshot_plan_for_session(
                session_id=effective_session_id,
                plan_file_path=snapshot_path,
                project_cwd=cwd,
                claude_installation=claude_installation,
                repo_root=repo_root,
            )
            # NOTE: Plan file deletion moved to impl_signal.py on 'started' event
            # This allows the user to modify and re-save the plan before implementing

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
        }
        if snapshot_result is not None:
            output_data["archived_to"] = str(snapshot_result.snapshot_dir)
        click.echo(json.dumps(output_data))
