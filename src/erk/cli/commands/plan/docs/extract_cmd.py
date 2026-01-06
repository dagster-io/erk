"""Command to mark a plan as having been analyzed for documentation."""

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
from erk_shared.output.output import user_output


@click.command("extract")
@click.argument("identifier", type=str)
@click.pass_obj
def extract_docs(ctx: ErkContext, identifier: str) -> None:
    """Mark a plan as having been analyzed for documentation.

    Adds the docs-extracted label to the specified issue, indicating that
    its session logs have been reviewed for documentation improvements.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse issue number
    issue_number = parse_issue_identifier(identifier)

    # Ensure label exists in repo (create if needed)
    try:
        ctx.issues.ensure_label_exists(
            repo_root=repo_root,
            label=DOCS_EXTRACTED_LABEL,
            description=DOCS_EXTRACTED_LABEL_DESCRIPTION,
            color=DOCS_EXTRACTED_LABEL_COLOR,
        )
    except RuntimeError as e:
        raise click.ClickException(f"Failed to ensure label exists: {e}") from e

    # Add label to issue (idempotent)
    try:
        ctx.issues.ensure_label_on_issue(repo_root, issue_number, DOCS_EXTRACTED_LABEL)
    except RuntimeError as e:
        raise click.ClickException(f"Failed to add label to issue #{issue_number}: {e}") from e

    user_output(f"Marked plan #{issue_number} as docs-extracted")
