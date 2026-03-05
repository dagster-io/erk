"""Teleport a PR's remote state to the local branch.

Ensures the PR exists on GitHub, fetches the remote branch, and force-resets
the local branch to match the remote exactly. Operates on the current worktree
by default, with --new-slot to create a fresh worktree slot.
"""

import click

from erk.cli.commands.checkout_helpers import ensure_branch_has_worktree
from erk.cli.commands.pr.checkout_cmd import _fetch_and_update_branch
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output


@click.command("teleport")
@click.argument("pr_number", type=int)
@click.option("--new-slot", is_flag=True, help="Create a new worktree slot")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def pr_teleport(ctx: ErkContext, pr_number: int, new_slot: bool, force: bool) -> None:
    """Teleport a PR's remote state to local, overwriting local branch.

    Ensures the PR exists on GitHub, fetches the latest remote state, and
    force-resets the local branch to match the remote exactly.

    \b
    Examples:
        erk pr teleport 123          # Overwrite current branch with PR #123's remote state
        erk pr teleport 123 -f       # Skip confirmation
        erk pr teleport 123 --new-slot  # Create a new worktree slot for the PR
    """
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Ensure PR exists
    ctx.console.info(f"Fetching PR #{pr_number}...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        ctx.console.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    if pr.is_cross_repository:
        ctx.console.error("Teleport is not supported for cross-repository (fork) PRs.")
        raise SystemExit(1)

    branch_name = pr.head_ref_name

    if new_slot:
        _teleport_new_slot(ctx, repo, pr_number=pr_number, branch_name=branch_name, force=force)
    else:
        _teleport_in_place(ctx, repo, pr_number=pr_number, branch_name=branch_name, force=force)


def _teleport_in_place(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    branch_name: str,
    force: bool,
) -> None:
    """Teleport by force-resetting the current branch to match remote."""
    cwd = ctx.cwd
    current_branch = ctx.git.branch.get_current_branch(cwd)

    if current_branch != branch_name:
        ctx.console.error(
            f"Current branch is '{current_branch}', but PR #{pr_number} is on '{branch_name}'.\n\n"
            f"Either checkout the correct branch first, or use --new-slot to create a worktree."
        )
        raise SystemExit(1)

    # Fetch latest remote state
    ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)

    # Show divergence info and confirm
    if not force:
        _confirm_overwrite(ctx, cwd=cwd, branch_name=branch_name)

    # Force-reset local branch to match remote
    ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)

    # Reset working tree to match the new branch head
    ctx.git.branch.checkout_branch(cwd, branch_name)

    user_output(
        click.style("Teleported ", fg="green")
        + click.style(branch_name, fg="cyan", bold=True)
        + click.style(f" to match remote (PR #{pr_number})", fg="green")
    )


def _teleport_new_slot(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    branch_name: str,
    force: bool,
) -> None:
    """Teleport into a new worktree slot, force-updating the branch."""
    # Check if branch already has a worktree
    existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        user_output(
            f"PR #{pr_number} already has a worktree at "
            + click.style(str(existing_worktree), fg="cyan", bold=True)
        )
        raise SystemExit(1)

    # Fetch and force-update local branch to match remote
    _fetch_and_update_branch(ctx, repo, branch_name=branch_name, pr_number=pr_number)

    # Create worktree slot
    worktree_path, _already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=False, force=force
    )

    user_output(
        click.style("Teleported ", fg="green")
        + click.style(branch_name, fg="cyan", bold=True)
        + click.style(f" (PR #{pr_number}) into ", fg="green")
        + click.style(str(worktree_path), fg="cyan", bold=True)
    )


def _confirm_overwrite(ctx: ErkContext, *, cwd, branch_name: str) -> None:
    """Show divergence info and ask for confirmation before overwriting."""
    try:
        ahead, behind = ctx.git.branch.get_ahead_behind(cwd, branch_name)
    except RuntimeError:
        ahead, behind = 0, 0

    if ahead == 0 and behind == 0:
        ctx.console.info("Branch is already in sync with remote. Nothing to teleport.")
        raise SystemExit(0)

    parts: list[str] = []
    if ahead > 0:
        parts.append(f"{ahead} local commit(s) ahead")
    if behind > 0:
        parts.append(f"{behind} commit(s) behind")
    status = ", ".join(parts)

    click.echo(
        click.style("Warning: ", fg="yellow")
        + f"Local branch '{branch_name}' is {status} of remote."
    )

    if ahead > 0:
        click.echo(click.style("  This will discard your local commits.", fg="yellow"))

    if not click.confirm("Overwrite local branch with remote state?"):
        click.echo("Aborted.")
        raise SystemExit(0)
