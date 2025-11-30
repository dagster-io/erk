"""Goto command - navigate directly to a worktree by name."""

import click
from erk_shared.output.output import user_output

from erk.cli.commands.completions import complete_worktree_names
from erk.cli.commands.navigation_helpers import activate_root_repo, activate_worktree
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("goto")
@click.argument("worktree_name", shell_complete=complete_worktree_names)
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.pass_obj
def goto_wt(ctx: ErkContext, worktree_name: str, script: bool) -> None:
    """Jump directly to a worktree by name.

    With shell integration (recommended):
      erk goto WORKTREE_NAME

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
      source <(erk goto WORKTREE_NAME --script)

    This will cd to the worktree, create/activate .venv, and load .env variables.

    Special keyword:
      erk goto root    # Jump to the root repository

    Example:
      erk goto feature-work    # Jump to worktree named "feature-work"
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Special case: "root" jumps to root repository
    if worktree_name == "root":
        activate_root_repo(ctx, repo, script, "goto")
        return  # _activate_root_repo raises SystemExit, but explicit return for clarity

    # Validate worktree exists
    worktree_path = repo.worktrees_dir / worktree_name

    if not ctx.git.path_exists(worktree_path):
        # Show available worktrees
        worktrees = ctx.git.list_worktrees(repo.root)
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
                "Use 'erk checkout' to switch by branch name."
            )

        raise SystemExit(1)

    # Get branch info for this worktree
    worktrees = ctx.git.list_worktrees(repo.root)
    target_worktree = None
    for wt in worktrees:
        if wt.path == worktree_path:
            target_worktree = wt
            break

    target_worktree = Ensure.not_none(
        target_worktree, f"Worktree '{worktree_name}' not found in git worktree list"
    )

    # Show worktree and branch info (only in non-script mode)
    if not script:
        branch_name = target_worktree.branch or "(detached HEAD)"
        styled_wt = click.style(worktree_name, fg="cyan", bold=True)
        styled_branch = click.style(branch_name, fg="yellow")
        user_output(f"Went to worktree {styled_wt} [{styled_branch}]")

    # Activate the worktree
    activate_worktree(ctx, repo, worktree_path, script, "goto")
