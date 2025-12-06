"""Land current PR and create pending extraction marker.

This command merges the PR, creates a "pending extraction" marker, and outputs
an activation script. The user stays in the worktree to extract insights before
manually deleting.

Workflow (default):
    1. erk pr land         # Merges PR, creates marker, stays in worktree
    2. claude /erk:create-raw-extraction-plan  # Extracts insights, deletes marker
    3. erk down --delete-current        # Manual cleanup when ready

Workflow (--skip-insights):
    1. erk pr land --skip-insights  # Merges PR, deletes worktree, goes to trunk
"""

import click
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess
from erk_shared.output.output import machine_output, user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.markers import PENDING_EXTRACTION_MARKER, create_marker


@click.command("land")
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.option(
    "--skip-insights",
    is_flag=True,
    help="Skip extraction marker; delete worktree and go to trunk",
)
@click.pass_obj
def pr_land(ctx: ErkContext, script: bool, skip_insights: bool) -> None:
    """Merge PR and create pending extraction marker.

    Merges the current PR (must be one level from trunk) and creates a
    ".erk/pending-extraction" marker in the worktree. The user stays in the
    worktree to run extraction before manual cleanup.

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

    After landing:
      claude /erk:create-raw-extraction-plan   # Extract insights (deletes marker)
      erk down --delete-current         # Manual cleanup

    With --skip-insights:
      Skips the extraction marker and automatically deletes the worktree
      and branch, navigating to trunk. Use when no session insights are needed.

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

    if skip_insights:
        # Skip marker creation, delete worktree and branch, go to trunk
        delete_branch_and_worktree(ctx, repo, current_branch, current_worktree_path)

        user_output("")
        user_output(click.style("✓", fg="green") + " Landed PR. Deleted worktree and branch.")

        # Output activation script pointing to trunk/root repo
        activate_root_repo(ctx, repo, script, command_name="pr-land")
        # activate_root_repo raises SystemExit(0)

    # Default behavior: create pending extraction marker and stay in worktree

    # Step 2: Create pending extraction marker
    # This signals that extraction should happen before worktree deletion
    create_marker(current_worktree_path, PENDING_EXTRACTION_MARKER)
    user_output(click.style("✓", fg="green") + " Created pending extraction marker")

    # Step 3: Output activation script (stays in current worktree)
    extraction_cmd = "claude /erk:create-raw-extraction-plan"
    script_content = render_activation_script(
        worktree_path=current_worktree_path,
        final_message=f'echo "Landed PR. Run {extraction_cmd} to extract insights."',
        comment="erk pr land activate-script",
    )
    activation_result = ctx.script_writer.write_activation_script(
        script_content,
        command_name="pr-land",
        comment="stay in worktree after landing",
    )
    machine_output(str(activation_result.path), nl=False)

    # Step 4: Output next steps
    user_output("")
    user_output(click.style("Next steps:", fg="cyan"))
    user_output("  1. Run: claude /erk:create-raw-extraction-plan")
    user_output("  2. Run: erk down --delete-current")
    user_output("")

    raise SystemExit(0)
