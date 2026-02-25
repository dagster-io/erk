"""Command to check a plan for duplicates and commit-history relevance."""

import sys
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.plan_duplicate_checker import PlanDuplicateChecker
from erk.core.plan_relevance_checker import PlanRelevanceChecker
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound


@click.command("duplicate-check")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Plan file to read",
)
@click.option(
    "--plan",
    "-p",
    type=str,
    help="Existing plan ID to check (fetches body and excludes self from comparison)",
)
@click.pass_obj
def duplicate_check_plan(
    ctx: ErkContext,
    file: Path | None,
    plan: str | None,
) -> None:
    """Check if a plan duplicates any existing open plans.

    Uses LLM inference to detect semantic duplicates — plans that aim to
    accomplish the same functional change, even if worded differently.

    Also checks whether the plan's work has already been implemented
    via recent commits merged to the trunk branch.

    Supports three input modes:
    - Plan ID: --plan ID (fetches plan body, excludes self from comparison)
    - File: --file PATH (recommended for automation)
    - Stdin: pipe content via shell (for Unix composability)

    Exit codes:
        0: No duplicates found and not already implemented
        1: Duplicates found, already implemented, or error

    Examples:
        erk pr duplicate-check --plan 200
        erk pr duplicate-check --file plan.md
        cat plan.md | erk pr duplicate-check
    """
    # Validate mutual exclusivity of --plan and --file
    if plan is not None and file is not None:
        Ensure.invariant(False, "Cannot use both --plan and --file. Choose one input mode.")

    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Resolve plan content and optional self-exclusion identifier
    exclude_plan_id: str | None = None

    if plan is not None:
        plan_number = parse_issue_identifier(plan)
        plan_id = str(plan_number)
        result = ctx.plan_store.get_plan(repo_root, plan_id)
        if isinstance(result, PlanNotFound):
            user_output(click.style("Error: ", fg="red") + f"Plan {plan_id} not found.")
            raise SystemExit(1)
        content = result.body
        exclude_plan_id = result.plan_identifier
    elif file is not None:
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
        Ensure.invariant(False, "No input provided. Use --plan, --file, or pipe content to stdin.")

    Ensure.not_empty(content.strip(), "Plan content is empty. Provide a non-empty plan.")

    has_problems = False

    # --- Duplicate check against existing open plans ---
    # Fetch existing open plans via plan_list_service (includes all plan PRs,
    # not just drafts — DraftPRPlanBackend.list_plans filters to draft=True
    # which misses undrafted impl-stage plans)
    if repo.github is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine repository owner/name")
        raise SystemExit(1)
    location = GitHubRepoLocation(
        root=repo_root,
        repo_id=GitHubRepoId(repo.github.owner, repo.github.repo),
    )
    plan_data = ctx.plan_list_service.get_plan_list_data(
        location=location,
        labels=["erk-planned-pr", "erk-plan"],
        state="open",
        skip_workflow_runs=True,
        http_client=None,
    )
    existing_plans = plan_data.plans

    # Server-side label AND (erk-planned-pr + erk-plan) now excludes learn plans.

    # When checking an existing plan, exclude it from the comparison set
    if exclude_plan_id is not None:
        existing_plans = [p for p in existing_plans if p.plan_identifier != exclude_plan_id]

    if not existing_plans:
        user_output("No existing open plans to compare against.")
    else:
        user_output(f"Checking against {len(existing_plans)} open plan(s):")
        for p in existing_plans:
            user_output(f"  #{p.plan_identifier}: {p.title}")
        user_output("")
        user_output("Analyzing for semantic duplicates...")
        user_output("")

        checker = PlanDuplicateChecker(ctx.prompt_executor)
        dup_result = checker.check(content, existing_plans)

        if dup_result.error is not None:
            user_output(click.style("Error: ", fg="red") + "Duplicate check failed:")
            user_output(f"  {dup_result.error}")
            has_problems = True

        if dup_result.has_duplicates:
            user_output(click.style("Potential duplicate(s) found:", fg="yellow"))
            user_output("")
            for match in dup_result.matches:
                user_output(f'  #{match.plan_id}: "{match.title}"')
                user_output(f"    {match.explanation}")
                user_output(f"    {match.url}")
                user_output("")
            has_problems = True

    # --- Relevance check against recent trunk commits ---
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    recent_commits = ctx.git.commit.get_recent_commits(repo_root, limit=20, branch=trunk_branch)

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
