"""Command to create a plan from markdown content."""

import sys
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.branch_slug_generator import generate_branch_slug
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.naming import generate_planned_pr_branch_name
from erk_shared.output.next_steps import format_plan_next_steps_plain
from erk_shared.output.output import user_output
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr
from erk_shared.plan_utils import extract_title_from_plan


@click.command("create")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Plan file to read",
)
@click.option("--title", "-t", type=str, help="Plan title (default: extract from H1)")
@click.option("--label", "-l", multiple=True, help="Additional labels")
@click.option("--summary", help="AI-generated summary to display above the collapsed plan")
@click.pass_obj
def pr_create(
    ctx: ErkContext,
    file: Path | None,
    title: str | None,
    label: tuple[str, ...],
    summary: str | None,
) -> None:
    """Create a plan as a draft PR from markdown content.

    Supports two input modes:
    - File: --file PATH (recommended for automation)
    - Stdin: pipe content via shell (for Unix composability)

    Examples:
        erk pr create --file plan.md
        cat plan.md | erk pr create
        erk pr create --file plan.md --title "Custom Title"
        erk pr create --file plan.md --label bug --label urgent
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
    elif not ctx.console.is_stdin_interactive():
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

    # Build labels: erk-pr + erk-plan + erk-core + any extra
    labels = ["erk-pr", "erk-plan", "erk-core"]
    for extra in label:
        if extra not in labels:
            labels.append(extra)

    # Determine source_repo for cross-repo plans
    # When plans_repo is configured, plans are stored in a separate repo
    # and source_repo records where implementation will happen
    source_repo: str | None = None
    plans_repo = ctx.local_config.github_repo if ctx.local_config else None
    if plans_repo is not None and repo.github is not None:
        source_repo = f"{repo.github.owner}/{repo.github.repo}"

    # Generate branch name with LLM slug
    slug = generate_branch_slug(
        ctx.prompt_executor,
        title if title is not None else extract_title_from_plan(content),
    )
    branch_name = generate_planned_pr_branch_name(slug, ctx.time.now(), objective_id=None)

    # Create plan as a draft PR
    result = create_plan_draft_pr(
        git=ctx.git,
        github=ctx.github,
        github_issues=ctx.issues,
        branch_manager=ctx.branch_manager,
        time=ctx.time,
        repo_root=repo_root,
        cwd=ctx.cwd,
        plan_content=content,
        branch_name=branch_name,
        title=title,
        labels=labels,
        source_repo=source_repo,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=None,
        summary=summary or "",
        extra_files=None,
    )

    if not result.success:
        user_output(click.style("Error: ", fg="red") + str(result.error))
        raise SystemExit(1)

    # Display success message with next steps
    user_output(f"Created plan #{result.pr_number}")
    user_output("")
    user_output(f"Plan: {result.pr_url}")
    user_output(f"Branch: {result.branch_name}")
    user_output("")
    if (
        result.pr_number is not None
        and result.branch_name is not None
        and result.pr_url is not None
    ):
        user_output(format_plan_next_steps_plain(result.pr_number, url=result.pr_url))
