"""Command to create a plan issue from markdown content."""

import sys
from pathlib import Path

import click
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
        ctx.plan_store.ensure_label(
            repo_root,
            label="erk-plan",
            description="Implementation plan tracked by erk",
            color="0E8A16",  # Green
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to ensure label exists: {e}")
        raise SystemExit(1) from e

    # Build labels list from additional labels (erk-plan added automatically by plan_store)
    labels = list(label)

    # Create plan using plan_store abstraction
    # (handles Schema V2: metadata in issue body, plan content in first comment)
    try:
        result = ctx.plan_store.create_plan(
            repo_root=repo_root,
            title=title,  # Without [erk-plan] suffix - plan_store adds it
            body=content,
            labels=labels,
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to create plan: {e}")
        raise SystemExit(1) from e

    # Display success message with next steps
    user_output(f"Created plan #{result.plan_identifier}")
    user_output("")
    user_output(f"Issue: {result.url}")
    user_output("")
    user_output("Next steps:")
    user_output(f"  View:       erk get {result.plan_identifier}")
    user_output(f"  Implement:  erk implement {result.plan_identifier}")
    user_output(f"  Submit:     erk submit {result.plan_identifier}")
