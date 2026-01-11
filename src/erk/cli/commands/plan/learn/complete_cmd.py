"""Command to complete a learn plan and mark source plans as extracted.

DEPRECATED: This command is deprecated because the source_plan_issues
metadata field has been removed from the schema.
"""

import click

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata.core import find_metadata_block


@click.command("complete")
@click.argument("identifier", type=str)
@click.pass_obj
def complete_learn(ctx: ErkContext, identifier: str) -> None:
    """Complete a learn plan by marking source plans as docs-extracted.

    DEPRECATED: This command is deprecated because the source_plan_issues
    metadata field has been removed from the schema.

    Args:
        identifier: Learn plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse learn plan issue number
    issue_number = parse_issue_identifier(identifier)

    # Fetch the learn plan issue to read its metadata
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

    # Check for erk-learn label
    if "erk-learn" not in issue_info.labels:
        raise click.ClickException(
            f"Issue #{issue_number} is not a learn plan (missing erk-learn label). "
            "This command only works on learn plans."
        )

    # source_plan_issues field has been removed from the schema
    # This command is deprecated and will be removed in a future version
    raise click.ClickException(
        "The 'complete' command is deprecated. "
        "source_plan_issues metadata field has been removed from the schema."
    )
