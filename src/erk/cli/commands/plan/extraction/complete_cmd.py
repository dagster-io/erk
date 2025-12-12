"""Command to complete an extraction plan and mark source plans as extracted."""

import click

from erk.cli.constants import (
    DOCS_EXTRACTED_LABEL,
    DOCS_EXTRACTED_LABEL_COLOR,
    DOCS_EXTRACTED_LABEL_DESCRIPTION,
)
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata import find_metadata_block
from erk_shared.output.output import user_output


@click.command("complete")
@click.argument("identifier", type=str)
@click.pass_obj
def complete_extraction(ctx: ErkContext, identifier: str) -> None:
    """Complete an extraction plan by marking source plans as docs-extracted.

    Reads the extraction plan's metadata to find source_plan_issues,
    then adds the docs-extracted label to each source plan.

    This command is idempotent - safe to run multiple times.

    Args:
        identifier: Extraction plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse extraction plan issue number
    issue_number = parse_issue_identifier(identifier)

    # Fetch the extraction plan issue to read its metadata
    try:
        issue_info = ctx.issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        raise click.ClickException(f"Failed to fetch issue #{issue_number}: {e}") from e

    # Extract plan-header metadata block
    plan_header = find_metadata_block(issue_info.body, "plan-header")
    if plan_header is None:
        raise click.ClickException(
            f"Issue #{issue_number} does not have a plan-header metadata block. "
            "Is this an erk plan issue?"
        )

    # Check plan_type
    plan_type = plan_header.data.get("plan_type")
    if plan_type != "extraction":
        raise click.ClickException(
            f"Issue #{issue_number} is not an extraction plan (plan_type: {plan_type}). "
            "This command only works on extraction plans."
        )

    # Get source_plan_issues
    source_plan_issues = plan_header.data.get("source_plan_issues")
    if not source_plan_issues:
        raise click.ClickException(
            f"Issue #{issue_number} has no source_plan_issues in its metadata. "
            "Cannot determine which plans to mark as extracted."
        )

    # Ensure docs-extracted label exists
    try:
        ctx.issues.ensure_label_exists(
            repo_root,
            DOCS_EXTRACTED_LABEL,
            DOCS_EXTRACTED_LABEL_DESCRIPTION,
            DOCS_EXTRACTED_LABEL_COLOR,
        )
    except RuntimeError as e:
        raise click.ClickException(f"Failed to ensure label exists: {e}") from e

    # Mark each source plan as docs-extracted
    marked_count = 0
    for source_issue_number in source_plan_issues:
        try:
            ctx.issues.ensure_label_on_issue(repo_root, source_issue_number, DOCS_EXTRACTED_LABEL)
            user_output(f"  Marked plan #{source_issue_number} as docs-extracted")
            marked_count += 1
        except RuntimeError as e:
            # Log the error but continue with other issues
            click.echo(f"  Warning: Failed to mark plan #{source_issue_number}: {e}", err=True)

    # Summary
    if marked_count == len(source_plan_issues):
        user_output(
            f"\nExtraction plan #{issue_number} completed: "
            f"marked {marked_count} source plan(s) as docs-extracted"
        )
    else:
        user_output(
            f"\nExtraction plan #{issue_number} partially completed: "
            f"marked {marked_count}/{len(source_plan_issues)} source plan(s) as docs-extracted"
        )
