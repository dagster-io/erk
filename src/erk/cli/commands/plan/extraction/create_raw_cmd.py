"""Command to create a raw extraction plan from session data."""

import json
from dataclasses import asdict

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, delete_marker


@click.command("raw")
@click.option(
    "--min-size",
    default=1024,
    type=int,
    help="Minimum session size in bytes for selection (default: 1024)",
)
@click.option(
    "--session-id",
    default=None,
    type=str,
    help="Current session ID (for extraction)",
)
@click.pass_obj
def create_raw(ctx: ErkContext, min_size: int, session_id: str | None) -> None:
    """Create extraction plan with raw session context.

    This command:
    1. Discovers Claude Code sessions in the project directory
    2. Auto-selects sessions based on branch context and size
    3. Preprocesses sessions to compressed XML format
    4. Creates a GitHub issue with erk-plan and erk-extraction labels
    5. Posts session content as chunked comments
    6. Deletes the pending-extraction marker if successful

    Output is JSON with success status, issue URL, and chunk count.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Call the orchestrator
    result = create_raw_extraction_plan(
        github_issues=ctx.issues,
        git=ctx.git,
        claude_installation=ctx.claude_installation,
        repo_root=repo_root,
        cwd=ctx.cwd,
        current_session_id=session_id,
        min_size=min_size,
    )

    # Delete pending extraction marker if successful
    if result.success:
        delete_marker(repo_root, PENDING_EXTRACTION_MARKER)

    # Output JSON result
    click.echo(json.dumps(asdict(result)))

    if not result.success:
        raise SystemExit(1)
