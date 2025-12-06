"""Land current PR, run extraction, and delete worktree.

This command merges the PR, automatically runs extraction, and deletes the worktree.
It combines what was previously three separate commands into one seamless flow.

Workflow:
    1. erk pr land  # Merges PR, extracts insights, prints URL, deletes worktree

Workflow (--skip-insights):
    1. erk pr land --skip-insights  # Merges PR, deletes worktree, goes to trunk
"""

import click
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.extraction.session_discovery import get_current_session_id
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess
from erk_shared.output.output import user_output

from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("land")
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.option(
    "--skip-insights",
    is_flag=True,
    help="Skip extraction; delete worktree and go to trunk",
)
@click.pass_obj
def pr_land(ctx: ErkContext, script: bool, skip_insights: bool) -> None:
    """Merge PR, run extraction, and delete worktree.

    Merges the current PR (must be one level from trunk), automatically runs
    extraction to capture session insights, then deletes the worktree and
    navigates to trunk.

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

    With --skip-insights:
      Skips extraction and just deletes the worktree.
      Use when no session insights are needed.

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

    # Step 2: Run extraction (unless --skip-insights)
    extraction_issue_url: str | None = None
    if not skip_insights:
        # Get current session ID from environment
        current_session_id = get_current_session_id()

        # Run extraction
        extraction_result = create_raw_extraction_plan(
            github_issues=ctx.issues,
            git=ctx.git,
            repo_root=repo.root,
            cwd=ctx.cwd,
            current_session_id=current_session_id,
        )

        if extraction_result.success:
            extraction_issue_url = extraction_result.issue_url
            user_output(
                click.style("✓", fg="green") + f" Extracted insights: {extraction_issue_url}"
            )
        else:
            # Extraction failed - warn but continue (PR was already merged)
            user_output(
                click.style("⚠", fg="yellow") + f" Extraction failed: {extraction_result.error}"
            )

    # Step 3: Delete worktree and branch, navigate to trunk
    delete_branch_and_worktree(ctx, repo, current_branch, current_worktree_path)
    user_output(click.style("✓", fg="green") + " Deleted worktree and branch")

    # Output activation script pointing to trunk/root repo
    activate_root_repo(ctx, repo, script, command_name="pr-land")
    # activate_root_repo raises SystemExit(0)
