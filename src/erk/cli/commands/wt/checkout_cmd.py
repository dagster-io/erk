"""Checkout command - navigate directly to a worktree by name."""

import click

from erk.cli.alias import alias
from erk.cli.commands.completions import complete_worktree_names
from erk.cli.commands.navigation_helpers import activate_root_repo, activate_worktree
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("worktree_name", shell_complete=complete_worktree_names)
@script_option
@click.pass_obj
def wt_checkout(ctx: ErkContext, worktree_name: str, script: bool) -> None:
    """Checkout a worktree by name.

    With shell integration (recommended):
      erk wt co WORKTREE_NAME

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
      source <(erk wt co WORKTREE_NAME --script)

    This will cd to the worktree, create/activate .venv, and load .env variables.

    Special keyword:
      erk wt co root    # Switch to the root repository

    Example:
      erk wt co feature-work    # Switch to worktree named "feature-work"
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Special case: "root" navigates to root repository
    if worktree_name == "root":
        activate_root_repo(ctx, repo, script, "co")
        return  # activate_root_repo raises SystemExit, but explicit return for clarity

    # Get all worktrees for error messages and lookup
    worktrees = ctx.git.list_worktrees(repo.root)

    # Validate worktree exists
    worktree_path = repo.worktrees_dir / worktree_name

    if not ctx.git.path_exists(worktree_path):
        # Show available worktrees (use already-fetched worktrees list)
        available_names = ["root"]
        for wt in worktrees:
            if not wt.is_root:
                available_names.append(wt.path.name)

        available_list = ", ".join(f"'{name}'" for name in sorted(available_names))
        user_output(
            click.style("Error:", fg="red")
            + f" Worktree '{worktree_name}' not found.\n\n"
            + f"Available worktrees: {available_list}\n\n"
            + "Use 'erk list' to see all worktrees with their branches."
        )

        # Check if the name looks like a branch (contains '/' or matches known branches)
        if "/" in worktree_name:
            user_output(
                "\nHint: It looks like you provided a branch name. "
                "Use 'erk br co' to switch by branch name."
            )

        raise SystemExit(1)

    # Get branch info for this worktree (use already-fetched worktrees list)
    target_worktree = None
    for wt in worktrees:
        if wt.path == worktree_path:
            target_worktree = wt
            break

    target_worktree = Ensure.not_none(
        target_worktree, f"Worktree '{worktree_name}' not found in git worktree list"
    )

    # Always navigate to worktree root and preserve relative path
    target_path = worktree_path

    # Show worktree and branch info (only in non-script mode)
    if not script:
        branch_name = target_worktree.branch or "(detached HEAD)"
        styled_wt = click.style(worktree_name, fg="cyan", bold=True)
        styled_branch = click.style(branch_name, fg="yellow")
        user_output(f"Went to worktree {styled_wt} [{styled_branch}]")

    # Activate the worktree
    activate_worktree(ctx, repo, target_path, script, "co", preserve_relative_path=True)
