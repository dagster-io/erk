"""Extract plan from ~/.claude/plans/ and create GitHub issue in one operation.

Usage:
    dot-agent run erk plan-save-to-issue [OPTIONS]

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
from erk_shared.extraction.session_context import collect_session_context
from erk_shared.github.metadata import render_session_content_blocks
from erk_shared.github.plan_issues import create_plan_issue

from dot_agent_kit.context_helpers import require_git, require_github_issues, require_repo_root
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan


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
    # Get GitHub Issues from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = Path.cwd()

    # Step 1: Extract plan (priority: plan_file > session_id > most recent)
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = get_latest_plan(str(cwd), session_id=session_id)

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

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=plan,
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

    # Step 8: Capture and embed session context (non-blocking)
    session_context_chunks = 0
    session_ids: list[str] = []

    git = require_git(ctx)
    session_result = collect_session_context(
        git=git, cwd=cwd, current_session_id=session_id, min_size=1024, limit=20
    )

    if session_result is not None and result.issue_number is not None:
        # Render and post as comments
        session_label = session_result.branch_context.current_branch or "planning-session"
        content_blocks = render_session_content_blocks(
            content=session_result.combined_xml,
            session_label=session_label,
            extraction_hints=["Planning session context for downstream analysis"],
        )

        # Post each block as a comment (failures are non-blocking)
        for block in content_blocks:
            try:
                github.add_comment(repo_root, result.issue_number, block)
                session_context_chunks += 1
            except RuntimeError:
                # Session context is supplementary - don't fail the command
                pass

        session_ids = session_result.session_ids

    # Step 9: Output success
    # Detect enrichment status for informational output
    is_enriched = "## Enrichment Details" in plan

    if output_format == "display":
        click.echo(f"Plan saved to GitHub issue #{result.issue_number}")
        click.echo(f"URL: {result.issue_url}")
        click.echo(f"Enrichment: {'Yes' if is_enriched else 'No'}")
        if session_context_chunks > 0:
            click.echo(f"Session context: {session_context_chunks} chunks")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": result.issue_number,
                    "issue_url": result.issue_url,
                    "title": result.title,
                    "enriched": is_enriched,
                    "session_context_chunks": session_context_chunks,
                    "session_ids": session_ids,
                }
            )
        )
