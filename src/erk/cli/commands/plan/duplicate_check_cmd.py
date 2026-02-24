"""Command to check a plan for duplicates and commit-history relevance."""

import sys
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.plan_duplicate_checker import PlanDuplicateChecker
from erk.core.plan_relevance_checker import PlanRelevanceChecker
from erk_shared.output.output import user_output


@click.command("duplicate-check")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Plan file to read",
)
@click.pass_obj
def duplicate_check_plan(
    ctx: ErkContext,
    file: Path | None,
) -> None:
    """Check if a plan duplicates any existing open plans.

    Uses LLM inference to detect semantic duplicates — plans that aim to
    accomplish the same functional change, even if worded differently.

    Also checks whether the plan's work has already been implemented
    via recent commits merged to the trunk branch.

    Supports two input modes:
    - File: --file PATH (recommended for automation)
    - Stdin: pipe content via shell (for Unix composability)

    Exit codes:
        0: No duplicates found and not already implemented
        1: Duplicates found, already implemented, or error

    Examples:
        erk plan duplicate-check --file plan.md
        cat plan.md | erk plan duplicate-check
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Read plan content from file or stdin
    if file is not None:
        Ensure.path_exists(ctx, file, f"File not found: {file}")
        try:
            content = file.read_text(encoding="utf-8")
        except OSError as e:
            user_output(click.style("Error: ", fg="red") + f"Failed to read file: {e}")
            raise SystemExit(1) from e
    elif not ctx.console.is_stdin_interactive():
        try:
            content = sys.stdin.read()
        except OSError as e:
            user_output(click.style("Error: ", fg="red") + f"Failed to read stdin: {e}")
            raise SystemExit(1) from e
    else:
        Ensure.invariant(False, "No input provided. Use --file or pipe content to stdin.")

    Ensure.not_empty(content.strip(), "Plan content is empty. Provide a non-empty plan.")

    has_problems = False

    # --- Duplicate check against existing open plans ---
    existing_plans = ctx.issues.list_issues(
        repo_root=repo_root,
        labels=["erk-plan"],
        state="open",
    )

    # Filter out erk-learn plans (different category)
    existing_plans = [p for p in existing_plans if "erk-learn" not in p.labels]

    if not existing_plans:
        user_output("No existing open plans to compare against.")
    else:
        user_output(f"Checking against {len(existing_plans)} open plan(s)...")
        user_output("")

        checker = PlanDuplicateChecker(ctx.prompt_executor)
        dup_result = checker.check(content, existing_plans)

        if dup_result.error is not None:
            user_output(
                click.style("Error: ", fg="red")
                + f"Duplicate check failed: {dup_result.error}"
            )
            has_problems = True

        if dup_result.has_duplicates:
            user_output(click.style("Potential duplicate(s) found:", fg="yellow"))
            user_output("")
            for match in dup_result.matches:
                user_output(f'  #{match.issue_number}: "{match.title}"')
                user_output(f"    {match.explanation}")
                user_output(f"    {match.url}")
                user_output("")
            has_problems = True

    # --- Relevance check against recent trunk commits ---
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    recent_commits = ctx.git.commit.get_recent_commits(
        repo_root, limit=20, branch=trunk_branch
    )

    if recent_commits:
        user_output(f"Checking against {len(recent_commits)} recent {trunk_branch} commit(s)...")
        user_output("")

        relevance_checker = PlanRelevanceChecker(ctx.prompt_executor)
        rel_result = relevance_checker.check(content, recent_commits)

        if rel_result.error is not None:
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Relevance check failed: {rel_result.error}"
            )
            # Relevance check errors don't block — just warn

        if rel_result.already_implemented:
            user_output(click.style("Work may already be implemented:", fg="yellow"))
            user_output("")
            for commit in rel_result.relevant_commits:
                user_output(f"  {commit.sha}: {commit.message}")
                user_output(f"    {commit.explanation}")
                user_output("")
            has_problems = True

    if has_problems:
        raise SystemExit(1)

    user_output(click.style("No duplicates found.", fg="green"))
    raise SystemExit(0)
