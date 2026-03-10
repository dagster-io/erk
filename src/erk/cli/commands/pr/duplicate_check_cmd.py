"""Command to check a plan for duplicates and commit-history relevance."""

import sys
import tempfile
from pathlib import Path

import click

from erk.cli.ensure import Ensure
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option
from erk.core.context import ErkContext
from erk.core.plan_duplicate_checker import PlanDuplicateChecker
from erk.core.plan_relevance_checker import PlanRelevanceChecker
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.output.output import user_output


@click.command("duplicate-check")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="PR file to read",
)
@click.option(
    "--plan",
    "-p",
    type=str,
    help="Existing PR ID to check (fetches body and excludes self from comparison)",
)
@resolved_repo_option
@click.pass_obj
def duplicate_check_plan(
    ctx: ErkContext,
    file: Path | None,
    plan: str | None,
    *,
    repo_id: GitHubRepoId,
) -> None:
    """Check if a plan duplicates any existing open plans.

    Uses LLM inference to detect semantic duplicates — plans that aim to
    accomplish the same functional change, even if worded differently.

    Also checks whether the plan's work has already been implemented
    via recent commits merged to the trunk branch (local mode only).

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
        erk pr duplicate-check --plan 200 --repo owner/repo
        cat plan.md | erk pr duplicate-check
    """
    if plan is not None and file is not None:
        Ensure.invariant(False, "Cannot use both --plan and --file. Choose one input mode.")

    # Resolve plan content
    exclude_plan_id: str | None = None
    content: str

    if plan is not None:
        remote = get_remote_github(ctx)
        plan_number = parse_issue_identifier(plan)
        issue = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=plan_number)
        if isinstance(issue, IssueNotFound):
            user_output(click.style("Error: ", fg="red") + f"PR {plan_number} not found.")
            raise SystemExit(1)
        content = issue.body
        exclude_plan_id = str(issue.number)
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

    Ensure.not_empty(content.strip(), "PR content is empty. Provide a non-empty PR.")

    has_problems = False

    http_client = ctx.http_client
    if http_client is None:
        user_output(click.style("Error: ", fg="red") + "GitHub authentication not available")
        raise SystemExit(1)

    # Determine location root (local vs remote)
    if not isinstance(ctx.repo, NoRepoSentinel):
        root = ctx.repo.root
    else:
        root = Path(tempfile.gettempdir()) / "erk-remote"

    location = GitHubRepoLocation(
        root=root,
        repo_id=repo_id,
    )
    plan_data = ctx.plan_list_service.get_plan_list_data(
        location=location,
        labels=["erk-pr"],
        state="open",
        skip_workflow_runs=True,
        http_client=http_client,
    )
    # Filter to plans only (title prefix check)
    existing_plans = [p for p in plan_data.plans if p.title.startswith("[erk-pr]")]

    if exclude_plan_id is not None:
        existing_plans = [p for p in existing_plans if p.pr_identifier != exclude_plan_id]

    if not existing_plans:
        user_output("No existing open PRs to compare against.")
    else:
        user_output(f"Checking against {len(existing_plans)} open PR(s):")
        for p in existing_plans:
            user_output(f"  #{p.pr_identifier}: {p.title}")
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
                user_output(f'  #{match.pr_id}: "{match.title}"')
                user_output(f"    {match.explanation}")
                user_output(f"    {match.url}")
                user_output("")
            has_problems = True

    # Trunk commit relevance check (local only)
    if not isinstance(ctx.repo, NoRepoSentinel):
        trunk_branch = ctx.git.branch.detect_trunk_branch(ctx.repo.root)
        recent_commits = ctx.git.commit.get_recent_commits(
            ctx.repo.root, limit=20, branch=trunk_branch
        )

        if recent_commits:
            user_output(
                f"Checking against {len(recent_commits)} recent {trunk_branch} commit(s)..."
            )
            user_output("")

            relevance_checker = PlanRelevanceChecker(ctx.prompt_executor)
            rel_result = relevance_checker.check(content, recent_commits)

            if rel_result.error is not None:
                user_output(
                    click.style("Warning: ", fg="yellow")
                    + f"Relevance check failed: {rel_result.error}"
                )

            if rel_result.already_implemented:
                user_output(click.style("Work may already be implemented:", fg="yellow"))
                user_output("")
                for commit in rel_result.relevant_commits:
                    user_output(f"  {commit.sha}: {commit.message}")
                    user_output(f"    {commit.explanation}")
                    user_output("")
                has_problems = True
    else:
        user_output(
            click.style("Note: ", dim=True)
            + "Trunk commit relevance check skipped (requires local git repository)"
        )

    if has_problems:
        raise SystemExit(1)

    user_output(click.style("No duplicates found.", fg="green"))
    raise SystemExit(0)
