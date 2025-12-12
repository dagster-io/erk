"""Land current PR, run extraction, and delete worktree.

This command merges the PR, automatically runs extraction, and deletes the worktree.
It combines what was previously three separate commands into one seamless flow.

Workflow (default, --no-insights):
    1. erk pr land  # Merges PR, deletes worktree, goes to trunk

Workflow (--insights):
    1. erk pr land --insights  # Merges PR, extracts insights, prints URL, deletes worktree

Note on extraction plans:
    PRs that originate from extraction plans (plan_type: "extraction") automatically
    skip insight extraction. This prevents infinite loops where extracting insights
    from an extraction-originated PR would lead to another extraction plan.
"""

from dataclasses import replace
from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
)
from erk.cli.commands.plan.check_cmd import (
    PlanValidationError,
    validate_plan_format,
)
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess
from erk_shared.output.output import user_output


def is_extraction_origin_pr(ctx: ErkContext, repo_root: Path, pr_number: int) -> bool:
    """Check if a PR originated from an extraction plan.

    Checks if the PR has the erk-skip-extraction label.

    Args:
        ctx: ErkContext with GitHub operations
        repo_root: Repository root directory
        pr_number: PR number to check

    Returns:
        True if the PR has the erk-skip-extraction label, False otherwise
    """
    return ctx.github.has_pr_label(repo_root, pr_number, ERK_SKIP_EXTRACTION_LABEL)


@click.command("land")
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.option(
    "--insights/--no-insights",
    default=False,
    help="Run extraction to capture session insights (default: --no-insights)",
)
@click.option(
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.pass_obj
def pr_land(ctx: ErkContext, script: bool, insights: bool, up_flag: bool) -> None:
    """Merge PR, run extraction, and delete worktree.

    Merges the current PR (must be one level from trunk), automatically runs
    extraction to capture session insights, then deletes the worktree and
    navigates to trunk.

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

    With --insights:
      Runs extraction to capture session insights before deleting worktree.
      Use when you want to preserve learnings from the session.

    Requires:
    - Graphite enabled: 'erk config set use_graphite true'
    - Current branch must be one level from trunk
    - PR must be open and ready to merge
    - Working tree must be clean (no uncommitted changes)
    """
    # Validate prerequisites
    Ensure.gh_authenticated(ctx)
    ensure_graphite_enabled(ctx)
    check_clean_working_tree(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch and worktree path before landing
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    current_worktree_path = Ensure.not_none(
        ctx.git.find_worktree_for_branch(repo.root, current_branch),
        f"Cannot find worktree for current branch '{current_branch}'.",
    )

    # Validate shell integration for activation script output
    if not script:
        user_output(
            click.style("Error: ", fg="red")
            + "This command requires shell integration for activation.\n\n"
            + "Options:\n"
            + "  1. Use shell integration: erk pr land\n"
            + "     (Requires 'erk init --shell' setup)\n\n"
            + "  2. Use --script flag: source <(erk pr land --script)\n"
        )
        raise SystemExit(1)

    # Validate --up preconditions BEFORE any mutations (fail-fast)
    target_child_branch: str | None = None
    if up_flag:
        children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)
        if len(children) == 0:
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has no children.\n"
                "Use 'erk pr land' without --up to return to trunk."
            )
            raise SystemExit(1)
        elif len(children) > 1:
            children_list = ", ".join(f"'{c}'" for c in children)
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has multiple children: "
                f"{children_list}.\n"
                "Use 'erk pr land' without --up, then 'erk co <branch>' to choose."
            )
            raise SystemExit(1)
        else:
            target_child_branch = children[0]

    # Step 1: Execute land-pr (merges the PR)
    # render_events() uses click.echo() + sys.stderr.flush() for immediate unbuffered output
    result = render_events(execute_land_pr(ctx, ctx.cwd))

    if isinstance(result, LandPrError):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)

    # Success - PR was merged
    success_result: LandPrSuccess = result
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{success_result.pr_number} [{success_result.branch_name}]"
    )

    # Check if this PR originated from an extraction plan
    # If so, automatically skip insights to prevent infinite extraction loops
    is_extraction_origin = is_extraction_origin_pr(ctx, repo.root, success_result.pr_number)

    if is_extraction_origin:
        user_output(
            click.style("ℹ", fg="cyan")
            + " PR originated from extraction plan - skipping insight extraction"
        )

    # Step 2: Run extraction (only if --insights and not extraction origin)
    extraction_issue_url: str | None = None
    if insights and not is_extraction_origin:
        # Get current session ID from session store
        current_session_id = ctx.session_store.get_current_session_id()

        # Show status line before extraction
        user_output(
            f"  Running: create_raw_extraction_plan("
            f"repo_root={repo.root}, session_id={current_session_id})"
        )

        # Run extraction
        extraction_result = create_raw_extraction_plan(
            github_issues=ctx.issues,
            git=ctx.git,
            session_store=ctx.session_store,
            repo_root=repo.root,
            cwd=ctx.cwd,
            current_session_id=current_session_id,
        )

        if extraction_result.success and extraction_result.issue_number is not None:
            extraction_issue_url = extraction_result.issue_url
            issue_number = extraction_result.issue_number

            # Validate plan format - halt on failure
            validation_result = validate_plan_format(ctx.issues, repo.root, issue_number)

            if isinstance(validation_result, PlanValidationError):
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Extraction plan #{issue_number} validation failed.\n"
                    + "The PR was merged but the worktree was NOT deleted.\n"
                    + f"Validation error: {validation_result.error}\n"
                    + f"Please investigate: {extraction_issue_url}\n"
                    + f"Run: erk plan check {issue_number}"
                )
                raise SystemExit(1)

            if validation_result.passed:
                user_output(
                    click.style("✓", fg="green") + f" Extracted insights: {extraction_issue_url}"
                )
            else:
                # Validation failed - halt before worktree deletion
                failed_checks = [desc for passed, desc in validation_result.checks if not passed]
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Extraction plan #{issue_number} failed validation.\n"
                    + "The PR was merged but the worktree was NOT deleted.\n"
                    + f"Failed checks: {', '.join(failed_checks)}\n"
                    + f"Please investigate: {extraction_issue_url}\n"
                    + f"Run: erk plan check {issue_number}"
                )
                raise SystemExit(1)
        elif not extraction_result.success:
            # Extraction failed - warn but continue (PR was already merged)
            user_output(
                click.style("⚠", fg="yellow") + f" Extraction failed: {extraction_result.error}"
            )

    # Step 3: Delete worktree and branch
    delete_branch_and_worktree(ctx, repo, current_branch, current_worktree_path)
    user_output(click.style("✓", fg="green") + " Deleted worktree and branch")

    # Create post-deletion repo context with root pointing to main_repo_root
    # (repo.root pointed to the now-deleted worktree)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    post_deletion_repo = replace(repo, root=main_repo_root)

    # Navigate to child branch (--up) or root
    if target_child_branch is not None:
        target_path = ctx.git.find_worktree_for_branch(main_repo_root, target_child_branch)
        if target_path is None:
            # Auto-create worktree for child
            target_path, _ = ensure_worktree_for_branch(
                ctx, post_deletion_repo, target_child_branch
            )
        activate_worktree(ctx, post_deletion_repo, target_path, script, command_name="pr-land")
        # activate_worktree raises SystemExit(0)
    else:
        # Output activation script pointing to trunk/root repo
        activate_root_repo(ctx, post_deletion_repo, script, command_name="pr-land")
        # activate_root_repo raises SystemExit(0)
