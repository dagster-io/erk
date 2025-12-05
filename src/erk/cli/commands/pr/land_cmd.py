"""Land current PR and navigate to parent branch.

This command replicates the shell function:

    land() {
        dot-agent kit-command gt land-pr && erk down --delete-current && git pull
    }

It merges the current PR, deletes the current worktree/branch, navigates to the
parent (trunk), and pulls the latest changes.
"""

import subprocess
from pathlib import Path

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
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


@click.command("land")
@click.argument("pr_reference", required=False)
@click.option("--script", is_flag=True, help="Print only the activation script")
@click.option("--up", is_flag=True, help="Navigate up to child branch instead of trunk")
@click.option(
    "--extract/--no-extract",
    default=True,
    help="Create extraction plan from session logs before landing (default: enabled)",
)
@click.pass_obj
def pr_land(ctx: ErkContext, pr_reference: str | None, script: bool, up: bool, extract: bool) -> None:
    """Merge PR, switch to trunk (or upstack with --up), and delete branch/worktree.

    Usage:
        erk pr land           # Land the current branch's PR
        erk pr land 123       # Land PR #123 by number
        erk pr land <url>     # Land PR from GitHub URL

    When landing by PR number:
    - Creates a temporary worktree for the PR's branch
    - Validates the branch is one level from trunk
    - Merges the PR and cleans up
    - Returns you to your starting location

    When landing the current branch:
    - Merges the current PR (must be one level from trunk)
    - Deletes the current branch and worktree
    - Navigates to trunk (or child branch with --up)
    - Pulls latest changes

    By default, creates a documentation extraction plan from session logs before
    landing (only for current branch landing). This captures learnings from the
    work session for future improvements. Use --no-extract to skip.

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

    # Dispatch based on whether PR reference was provided
    if pr_reference is not None:
        # Reject --up flag when landing by PR number
        if up:
            ctx.feedback.error("--up flag is not supported when landing by PR number")
            raise SystemExit(1)

        pr_number = parse_pr_reference(pr_reference)
        _land_pr_by_number(ctx, repo, pr_number, script)
    else:
        _land_current_branch(ctx, repo, script, up, extract)


def _land_current_branch(
    ctx: ErkContext, repo: RepoContext, script: bool, up: bool, extract: bool
) -> None:
    """Land the current branch's PR.

    Merges the current PR, deletes the current branch and worktree,
    then navigates to trunk (or child branch with --up).
    """
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
    extraction_success = True  # Default: proceed with deletion
    if extract:
        try:
            issue_url = ctx.shell.run_claude_extraction_plan(ctx.cwd)
            msg = click.style("✓", fg="green") + " Created documentation extraction plan"
            if issue_url:
                msg += f"\n  {issue_url}"
            user_output(msg)
        except subprocess.CalledProcessError as e:
            extraction_success = False
            user_output(
                click.style("⚠", fg="yellow")
                + " Extraction plan failed - preserving worktree for manual retry"
            )
            user_output(f"  Error: {e}")
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


def _land_pr_by_number(ctx: ErkContext, repo: RepoContext, pr_number: int, script: bool) -> None:
    """Land a PR by number, creating a temporary worktree if needed.

    This flow:
    1. Fetches PR info from GitHub
    2. Validates PR state (must be OPEN, not cross-repo)
    3. Creates/finds worktree for the branch
    4. Validates branch is one level from trunk
    5. Executes the land operation
    6. Outputs activation script (before cleanup)
    7. Cleans up worktree and branch
    8. Pulls trunk
    """
    # Save starting location for return
    starting_cwd = ctx.cwd

    # Step 1: Fetch PR info
    ctx.feedback.info(f"Fetching PR #{pr_number}...")
    pr_info = ctx.github.get_pr_checkout_info(repo.root, pr_number)
    if pr_info is None:
        ctx.feedback.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    # Step 2: Validate PR state
    if pr_info.state != "OPEN":
        ctx.feedback.error(
            f"PR #{pr_number} is {pr_info.state}, not OPEN.\nOnly open PRs can be landed."
        )
        raise SystemExit(1)

    # Step 3: Validate not cross-repository (fork PRs not supported)
    if pr_info.is_cross_repository:
        ctx.feedback.error(
            f"PR #{pr_number} is from a fork (cross-repository PR).\n\n"
            "Landing fork PRs is not supported.\n"
            "Use 'gh pr merge' directly instead:\n"
            f"  gh pr merge {pr_number} --squash"
        )
        raise SystemExit(1)

    branch_name = pr_info.head_ref_name

    # Step 4: Create/find worktree for the branch
    worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, branch_name)

    # Helper to clean up worktree if we created it and need to abort
    def cleanup_if_created() -> None:
        if was_created:
            ctx.git.remove_worktree(repo.root, worktree_path, force=True)
            ctx.git.prune_worktrees(repo.root)

    # Step 5: Validate branch is one level from trunk BEFORE merging
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, branch_name)

    if parent_branch != trunk_branch:
        cleanup_if_created()
        ctx.feedback.error(
            f"Branch '{branch_name}' is not one level from trunk.\n"
            f"Parent is '{parent_branch}', expected '{trunk_branch}'.\n\n"
            "The branch must be a direct child of trunk to land via PR number."
        )
        raise SystemExit(1)

    # Step 6: Execute land-pr (merges the PR)
    result = render_events(execute_land_pr(ctx, worktree_path))

    if isinstance(result, LandPrError):
        cleanup_if_created()
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)

    # Success - PR was merged
    success_result: LandPrSuccess = result
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{success_result.pr_number} [{success_result.branch_name}]"
    )

    # Step 7: Output activation script BEFORE cleanup
    # We return to starting location (not trunk) when landing by PR number
    dest_path = _determine_return_destination(ctx, starting_cwd, repo.root)
    dest_description = "starting location"

    if script:
        final_msg = f'echo "Landed PR #{pr_number} and returned to {dest_description}: $(pwd)"'
        script_content = render_activation_script(
            worktree_path=dest_path,
            final_message=final_msg,
            comment="erk pr land activate-script",
        )
        activation_result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="pr-land",
            comment=f"activate {dest_description} after landing PR #{pr_number}",
        )
        machine_output(str(activation_result.path), nl=False)

    # Step 8: Delete branch and worktree
    delete_branch_and_worktree(ctx, repo.root, branch_name, worktree_path)

    # Step 9: Pull trunk
    ctx.git.pull_branch(repo.root, "origin", trunk_branch, ff_only=True)
    user_output(click.style("✓", fg="green") + " Pulled latest changes to trunk")

    raise SystemExit(0)


def _determine_return_destination(ctx: ErkContext, starting_cwd: Path, repo_root: Path) -> Path:
    """Determine where to return after landing a PR by number.

    If the starting cwd still exists, return there.
    Otherwise, fall back to the repo root.
    """
    if ctx.git.path_exists(starting_cwd):
        return starting_cwd
    return repo_root
