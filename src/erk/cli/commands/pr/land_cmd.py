"""Land current PR and navigate to parent branch.

This command replicates the shell function:

    land() {
        dot-agent kit-command gt land-pr && erk down --delete-current && git pull
    }

It merges the current PR, deletes the current worktree/branch, navigates to the
parent (trunk), and pulls the latest changes.
"""

import click
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess
from erk_shared.output.output import machine_output, user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.navigation_helpers import (
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
    resolve_up_navigation,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("land")
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.option("--up", is_flag=True, help="Navigate up to child branch instead of trunk")
@click.option(
    "--extract/--no-extract",
    default=True,
    help="Create extraction plan from session logs before landing (default: enabled)",
)
@click.pass_obj
def pr_land(ctx: ErkContext, script: bool, up: bool, extract: bool) -> None:
    """Merge PR, switch to trunk (or upstack with --up), and delete branch/worktree.

    Merges the current PR (must be one level from trunk), deletes the current
    branch and worktree, then navigates to the destination and pulls changes.

    By default, creates a documentation extraction plan from session logs before
    landing. This captures learnings from the work session for future improvements.
    Use --no-extract to skip extraction plan creation.

    By default, navigates to trunk. With --up, navigates to child branch instead,
    enabling landing an entire stack one PR at a time.

    With shell integration (recommended):
      erk pr land               # Navigate to trunk, create extraction plan
      erk pr land --up          # Navigate to child, create extraction plan
      erk pr land --no-extract  # Skip extraction plan creation

    Without shell integration:
      source <(erk pr land --script)
      source <(erk pr land --up --script)

    Requires:
    - Graphite enabled: 'erk config set use_graphite true'
    - Current branch must be one level from trunk
    - PR must be open and ready to merge
    - Working tree must be clean (no uncommitted changes)
    - Claude CLI installed (for extraction plan; warns if missing)
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

    # Validate shell integration for worktree deletion
    # This check happens BEFORE any destructive operations (PR merge, worktree deletion)
    # A subprocess cannot change its parent shell's working directory, so without
    # shell integration, the shell will be stranded in the deleted worktree directory.
    if not script:
        user_output(
            click.style("Error: ", fg="red")
            + "This command deletes the current worktree and requires shell integration.\n\n"
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

    # Step 1.5: Create extraction plan from session logs (optional)
    # This captures learnings from the work session for documentation improvements.
    # Use ctx.cwd (current working directory) to access session logs in the worktree.
    # If extraction fails, preserve the worktree so user can retry manually.
    # Launch Claude interactively so the user can participate in the extraction workflow.
    extraction_success = True  # Default: proceed with deletion
    if extract:
        exit_code = ctx.claude_executor.execute_interactive_command(
            "/erk:create-extraction-plan",
            ctx.cwd,
        )
        extraction_success = exit_code == 0
        if extraction_success:
            user_output(click.style("✓", fg="green") + " Created documentation extraction plan")
        else:
            user_output(
                click.style("⚠", fg="yellow")
                + " Extraction plan failed - preserving worktree for manual retry"
            )
            user_output("  Run manually: claude /erk:create-extraction-plan")

    # Step 2: Navigate to destination (trunk or upstack)
    worktrees = ctx.git.list_worktrees(repo.root)

    if up:
        # Navigate up to child branch
        dest_branch, _was_created = resolve_up_navigation(ctx, repo, current_branch, worktrees)
        target_wt_path = ctx.git.find_worktree_for_branch(repo.root, dest_branch)
        dest_path = Ensure.not_none(target_wt_path, f"Worktree not found for '{dest_branch}'")
        dest_description = f"upstack branch '{dest_branch}'"
    else:
        # Navigate down to trunk (current behavior)
        dest_branch = ctx.git.detect_trunk_branch(repo.root)
        trunk_wt_path = ctx.git.find_worktree_for_branch(repo.root, dest_branch)

        if trunk_wt_path is not None and trunk_wt_path == repo.root:
            dest_path = repo.root
        elif trunk_wt_path is not None:
            dest_path = trunk_wt_path
        else:
            dest_path = repo.root
        dest_description = "trunk"

    # NOTE: We intentionally do NOT call safe_chdir() here.
    # A subprocess cannot change the parent shell's cwd.
    # The shell integration (activation script) handles the cd.

    # Step 3: Output activation script BEFORE destructive operations
    # This ensures the shell can navigate even if later steps fail.
    # The handler will use this script instead of passthrough when available.
    script_content = render_activation_script(
        worktree_path=dest_path,
        final_message=f'echo "Landed PR and switched to {dest_description}: $(pwd)"',
        comment="erk pr land activate-script",
    )
    activation_result = ctx.script_writer.write_activation_script(
        script_content,
        command_name="pr-land",
        comment=f"activate {dest_description} after landing",
    )
    machine_output(str(activation_result.path), nl=False)

    # Step 4: Delete current branch and worktree (skip if extraction failed)
    if extraction_success:
        delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)
    else:
        user_output(
            click.style("⚠", fg="yellow") + f" Worktree preserved at: {current_worktree_path}"
        )
        user_output("  Delete manually after extraction: erk wt rm")

    # Step 5: Pull latest changes on destination branch
    # If this fails, the script is already output - shell can still navigate
    ctx.git.pull_branch(dest_path, "origin", dest_branch, ff_only=True)
    user_output(click.style("✓", fg="green") + " Pulled latest changes")

    raise SystemExit(0)
