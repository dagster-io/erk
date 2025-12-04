"""Command to create a plan issue from markdown content."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.metadata import format_plan_content_comment, format_plan_header_body
from erk_shared.output.output import user_output
from erk_shared.plan_utils import extract_title_from_plan

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


@click.command("create")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Plan file to read",
)
@click.option("--title", "-t", type=str, help="Issue title (default: extract from H1)")
@click.option("--label", "-l", multiple=True, help="Additional labels")
@click.pass_obj
def create_plan(
    ctx: ErkContext,
    file: Path | None,
    title: str | None,
    label: tuple[str, ...],
) -> None:
    """Create a plan issue from markdown content.

    Supports two input modes:
    - File: --file PATH (recommended for automation)
    - Stdin: pipe content via shell (for Unix composability)

    Examples:
        erk create --file plan.md
        cat plan.md | erk create
        erk create --file plan.md --title "Custom Title"
        erk create --file plan.md --label bug --label urgent
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # LBYL: Check input sources - exactly one required
    # Priority: --file flag takes precedence over stdin
    content = ""  # Initialize to ensure type safety
    if file is not None:
        # Use file input
        Ensure.path_exists(ctx, file, f"File not found: {file}")
        try:
            content = file.read_text(encoding="utf-8")
        except OSError as e:
            user_output(click.style("Error: ", fg="red") + f"Failed to read file: {e}")
            raise SystemExit(1) from e
    elif not sys.stdin.isatty():
        # Use stdin input (piped data)
        try:
            content = sys.stdin.read()
        except OSError as e:
            user_output(click.style("Error: ", fg="red") + f"Failed to read stdin: {e}")
            raise SystemExit(1) from e
    else:
        # No input provided
        Ensure.invariant(False, "No input provided. Use --file or pipe content to stdin.")

    # Validate content is not empty
    Ensure.not_empty(content.strip(), "Plan content is empty. Provide a non-empty plan.")

    # Extract or use provided title
    if title is None:
        title = extract_title_from_plan(content)

    # Validate title is not empty
    Ensure.not_empty(
        title.strip(), "Could not extract title from plan. Use --title to specify one."
    )

    # Ensure erk-plan label exists
    try:
        ctx.issues.ensure_label_exists(
            repo_root,
            label="erk-plan",
            description="Implementation plan tracked by erk",
            color="0E8A16",  # Green
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to ensure label exists: {e}")
        raise SystemExit(1) from e

    # Build labels list: erk-plan + additional labels
    labels = ["erk-plan"] + list(label)

    # Create timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Get creator from GitHub authentication
    creator = ctx.issues.get_current_username()
    if not creator:
        creator = "unknown"

    # Format issue body (Schema V2: metadata only, worktree_name set later)
    issue_body = format_plan_header_body(
        created_at=timestamp,
        created_by=creator,
    )

    # Create the issue (add [erk-plan] suffix for visibility)
    issue_title = f"{title} [erk-plan]"
    try:
        result = ctx.issues.create_issue(
            repo_root=repo_root,
            title=issue_title,
            body=issue_body,
            labels=labels,
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to create issue: {e}")
        raise SystemExit(1) from e

    # Add plan content as first comment (Schema V2 format)
    try:
        comment_body = format_plan_content_comment(content)
        ctx.issues.add_comment(repo_root, result.number, comment_body)
    except RuntimeError as e:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Issue created but failed to add plan comment: {e}"
        )
        user_output(f"Issue #{result.number} created but incomplete.")
        user_output(f"URL: {result.url}")
        raise SystemExit(1) from e

    # Display success message with next steps
    user_output(f"Created plan #{result.number}")
    user_output("")
    user_output(f"Issue: {result.url}")
    user_output("")
    user_output("Next steps:")
    user_output(f"  View:       erk get {result.number}")
    user_output(f"  Implement:  erk implement {result.number}")
    user_output(f"  Submit:     erk submit {result.number}")
