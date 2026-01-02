"""Command to create a plan issue from markdown content."""

import sys
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.output.output import user_output


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

    # Convert extra labels tuple to list
    extra_labels = list(label) if label else None

    # Determine source_repo for cross-repo plans
    # When plans_repo is configured, plans are stored in a separate repo
    # and source_repo records where implementation will happen
    source_repo: str | None = None
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
    if plans_repo is not None and repo.github is not None:
        source_repo = f"{repo.github.owner}/{repo.github.repo}"

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=ctx.issues,
        repo_root=repo_root,
        plan_content=content,
        title=title,
        plan_type=None,
        extra_labels=extra_labels,
        title_suffix=None,
        source_plan_issues=None,
        extraction_session_ids=None,
        source_repo=source_repo,
        objective_issue=None,
    )

    if not result.success:
        if result.issue_number is not None:
            # Partial success - issue created but comment failed
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Issue created but failed to add plan comment: {result.error}"
            )
            user_output(f"Issue #{result.issue_number} created but incomplete.")
            user_output(f"URL: {result.issue_url}")
        else:
            user_output(click.style("Error: ", fg="red") + str(result.error))
        raise SystemExit(1)

    # Display success message with next steps
    user_output(f"Created plan #{result.issue_number}")
    user_output("")
    user_output(f"Issue: {result.issue_url}")
    user_output("")
    user_output("Next steps:")
    user_output(f"  View:       erk get {result.issue_number}")
    user_output(f"  Implement:  erk implement {result.issue_number}")
    user_output(f"  Submit:     erk submit {result.issue_number}")
