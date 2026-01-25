"""Checkout command - navigate directly to a worktree by name."""

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.commands.completions import complete_worktree_names
from erk.cli.commands.navigation_helpers import activate_root_repo
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.output.output import user_output


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("worktree_name", shell_complete=complete_worktree_names)
@script_option
@click.pass_obj
def wt_checkout(ctx: ErkContext, worktree_name: str, script: bool) -> None:
    """Checkout a worktree by name.

    Navigate to target worktree:
      source <(erk wt co WORKTREE_NAME --script)

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
        activate_root_repo(
            ctx,
            repo=repo,
            script=script,
            command_name="co",
            post_cd_commands=None,
            source_branch=None,
            force=False,
        )
        return  # activate_root_repo raises SystemExit, but explicit return for clarity

    # Get all worktrees for error messages and lookup
    worktrees = ctx.git.worktree.list_worktrees(repo.root)

    # Validate worktree exists
    worktree_path = repo.worktrees_dir / worktree_name

    if not ctx.git.worktree.path_exists(worktree_path):
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

    # Navigate to worktree
    branch_name = target_worktree.branch or "(detached HEAD)"
    styled_wt = click.style(worktree_name, fg="cyan", bold=True)
    styled_branch = click.style(branch_name, fg="yellow")

    # Compute relative path to preserve directory position
    relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name="co",
        script_message=f'echo "Went to worktree {styled_wt} [{styled_branch}]"',
        relative_path=relative_path,
        post_cd_commands=None,
    )

    if should_output:
        user_output(f"Worktree {styled_wt} [{styled_branch}]")
        activation_script_path = ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            activation_script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
        )
