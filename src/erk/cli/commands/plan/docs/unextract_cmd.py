"""Command to remove the docs-extracted label from a plan (for re-analysis)."""

import click

from erk.cli.constants import DOCS_EXTRACTED_LABEL
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


@click.command("unextract")
@click.argument("identifier", type=str)
@click.pass_obj
def unextract_docs(ctx: ErkContext, identifier: str) -> None:
    """Remove the docs-extracted label from a plan (for re-analysis).

    Removes the docs-extracted label from the specified issue, allowing it
    to appear again in the unextracted list for future documentation review.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse issue number
    issue_number = parse_issue_identifier(identifier)

    # Remove label from issue
    try:
        ctx.issues.remove_label_from_issue(repo_root, issue_number, DOCS_EXTRACTED_LABEL)
    except RuntimeError as e:
        raise click.ClickException(f"Failed to remove label from issue #{issue_number}: {e}") from e

    user_output(f"Removed docs-extracted label from plan #{issue_number}")
