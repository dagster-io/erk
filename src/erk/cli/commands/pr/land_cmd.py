"""Land current PR and navigate to parent branch.

This command replicates the shell function:

    land() {
        dot-agent kit-command gt land-pr && erk down --delete-current && git pull
    }

It merges the current PR, deletes the current worktree/branch, navigates to the
parent (trunk), and pulls the latest changes.
"""

import click
from erk_shared.integrations.gt.kit_cli_commands.gt.land_pr import (
    LandPrError,
    LandPrSuccess,
    execute_land_pr,
)
from erk_shared.output.output import machine_output, user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.navigation_helpers import (
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("land")
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.pass_obj
def pr_land(ctx: ErkContext, script: bool) -> None:
    """Land current PR and navigate to parent branch.

    Merges the current PR (must be one level from trunk), deletes the current
    branch and worktree, navigates to trunk, and pulls the latest changes.

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

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

    # Step 1: Execute land-pr (merges the PR)
    result = execute_land_pr()

    if isinstance(result, LandPrError):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)

    # Success - PR was merged
    success_result: LandPrSuccess = result
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{success_result.pr_number} [{success_result.branch_name}]"
    )

    # Step 2: Navigate to trunk (since land-pr validates parent is trunk)
    # The parent is always trunk after a successful land-pr
    trunk_branch = ctx.git.detect_default_branch(repo.root, ctx.trunk_branch)

    # Find where trunk is checked out
    trunk_wt_path = ctx.git.find_worktree_for_branch(repo.root, trunk_branch)

    # Determine destination path (root repo or trunk worktree)
    if trunk_wt_path is not None and trunk_wt_path == repo.root:
        # Trunk is in root repository
        dest_path = repo.root
    elif trunk_wt_path is not None:
        # Trunk has a dedicated worktree
        dest_path = trunk_wt_path
    else:
        # Trunk has no worktree, use root repo
        dest_path = repo.root

    # Change to destination before deleting current worktree
    # This prevents "cwd no longer exists" errors if user doesn't source activation script
    ctx.git.safe_chdir(dest_path)

    # Step 3: Delete current branch and worktree
    delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)

    # Step 4: Pull latest changes on trunk
    # Note: We pull from the destination path, not cwd (which is being deleted)
    ctx.git.pull_branch(dest_path, "origin", trunk_branch, ff_only=True)
    user_output(click.style("✓", fg="green") + " Pulled latest changes")

    # Step 5: Output activation script or message
    if script:
        script_content = render_activation_script(
            worktree_path=dest_path,
            final_message='echo "Landed PR and switched to trunk: $(pwd)"',
            comment="erk pr land activate-script",
        )
        activation_result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="pr-land",
            comment="activate trunk after landing",
        )
        machine_output(str(activation_result.path), nl=False)
    else:
        user_output(f"\nWent to: {dest_path}")
        user_output(
            "\nShell integration not detected. "
            "Run 'erk init --shell' to set up automatic activation."
        )
        user_output("Or use: source <(erk pr land --script)")

    raise SystemExit(0)
