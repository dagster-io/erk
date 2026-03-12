"""Teleport a PR's remote state to the local branch.

Remote-first counterpart to 'checkout'. While checkout preserves local state
(reusing existing worktrees, keeping unpushed commits), teleport force-resets
the local branch to match the remote exactly. Use teleport when a remote agent
has pushed commits and you want your local copy to match.

Operates on the current worktree by default, with --new-slot to create a fresh
worktree slot.
"""

from contextlib import nullcontext
from pathlib import Path

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.commands.checkout_helpers import (
    ensure_branch_has_worktree,
    navigate_and_display_checkout,
    script_error_handler,
)
from erk.cli.commands.pr.checkout_cmd import _fetch_and_update_branch
from erk.cli.commands.slot.common import find_assignment_by_worktree, update_slot_assignment_tip
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.gateway.github.types import PRNotFound


@click.command("teleport", cls=CommandWithHiddenOptions)
@click.argument("pr_number", type=int)
@click.option("--new-slot", is_flag=True, help="Create a new worktree slot")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--sync", is_flag=True, help="Run gt submit after teleport to sync with Graphite")
@script_option
@click.pass_obj
def pr_teleport(
    ctx: ErkContext, pr_number: int, new_slot: bool, force: bool, sync: bool, script: bool
) -> None:
    """Teleport a PR's remote state to local, overwriting local branch.

    Unlike 'checkout' which preserves local state (reusing existing worktrees
    and keeping local commits), teleport is remote-first: it force-resets the
    local branch to match the remote exactly, discarding any local commits
    that haven't been pushed.

    \b
    Use 'checkout' when you want to start working on a PR locally.
    Use 'teleport' when a remote agent has pushed new commits and you
    want your local branch to match the remote exactly.

    \b
    Examples:
        erk pr teleport 123              # Overwrite current branch with PR #123's remote state
        erk pr teleport 123 -f           # Skip confirmation
        erk pr teleport 123 --new-slot   # Create a new worktree slot for the PR
        erk pr teleport 123 --new-slot --script --sync  # Full setup with Graphite sync
    """
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    if script:
        ctx_manager = script_error_handler(ctx)
    else:
        ctx_manager = nullcontext()
    with ctx_manager:
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
        base_ref_name = pr.base_ref_name

        if new_slot:
            _teleport_new_slot(
                ctx,
                repo,
                pr_number=pr_number,
                branch_name=branch_name,
                base_ref_name=base_ref_name,
                force=force,
                sync=sync,
                script=script,
            )
        else:
            _teleport_in_place(
                ctx,
                repo,
                pr_number=pr_number,
                branch_name=branch_name,
                base_ref_name=base_ref_name,
                force=force,
                sync=sync,
                script=script,
            )


def _navigate_to_existing_worktree(
    ctx: ErkContext,
    *,
    repo_root: Path,
    pr_number: int,
    branch_name: str,
    script: bool,
) -> None:
    """Check if branch is already in a worktree; if so, navigate and exit."""
    existing = ctx.git.worktree.find_worktree_for_branch(repo_root, branch_name)
    if existing is None:
        return  # Not found, caller continues
    navigate_and_display_checkout(
        ctx,
        worktree_path=existing,
        branch_name=branch_name,
        script=script,
        command_name="pr-teleport",
        already_existed=True,
        existing_message=(
            f"PR #{pr_number} branch "
            + click.style(f"'{branch_name}'", fg="cyan", bold=True)
            + " is already checked out at {styled_path}"
        ),
        new_message="",
        script_message_existing=f'echo "PR #{pr_number} already checked out at $(pwd)"',
        script_message_new="",
        post_cd_commands=None,
    )
    if not script:
        script_path = ensure_worktree_activate_script(
            worktree_path=existing,
            post_create_commands=None,
        )
        print_activation_instructions(
            script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=False,
        )
    raise SystemExit(0)


def _teleport_in_place(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    branch_name: str,
    base_ref_name: str,
    force: bool,
    sync: bool,
    script: bool,
) -> None:
    """Teleport by force-resetting the current branch to match remote."""
    cwd = ctx.cwd
    current_branch = ctx.git.branch.get_current_branch(cwd)

    if current_branch != branch_name:
        _navigate_to_existing_worktree(
            ctx,
            repo_root=repo.root,
            pr_number=pr_number,
            branch_name=branch_name,
            script=script,
        )
        # Branch not in any worktree — proceed; checkout below will switch branches

    # Fetch latest remote state
    ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)

    # Show divergence info and confirm (only if the branch already exists locally)
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    if branch_name in local_branches and not force:
        _confirm_overwrite(ctx, cwd=cwd, branch_name=branch_name)

    # Force-reset local branch to match remote
    ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)

    # Reset working tree to match the new branch head
    ctx.git.branch.checkout_branch(cwd, branch_name)

    # Slot awareness: update assignment if in a managed slot (matches erk br co)
    state = load_pool_state(repo.pool_json_path)
    if state is not None:
        current_assignment = find_assignment_by_worktree(state, ctx.git, cwd)
        if current_assignment is not None:
            update_slot_assignment_tip(
                repo.pool_json_path,
                state,
                current_assignment,
                branch_name=branch_name,
                now=ctx.time.now().isoformat(),
            )

    # Register with Graphite (track/retrack for all PRs, fetch base for stacked)
    _register_with_graphite(ctx, repo, branch_name=branch_name, base_ref_name=base_ref_name)

    post_cd_commands = ["gt submit --no-interactive"] if sync else None

    navigate_and_display_checkout(
        ctx,
        worktree_path=cwd,
        branch_name=branch_name,
        script=script,
        command_name="pr-teleport",
        already_existed=False,
        existing_message="",
        new_message=(
            click.style("Teleported ", fg="green")
            + click.style(branch_name, fg="cyan", bold=True)
            + click.style(f" to match remote (PR #{pr_number})", fg="green")
        ),
        script_message_existing="",
        script_message_new=f'echo "Teleported {branch_name} to match remote (PR #{pr_number})"',
        post_cd_commands=post_cd_commands,
    )


def _teleport_new_slot(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    branch_name: str,
    base_ref_name: str,
    force: bool,
    sync: bool,
    script: bool,
) -> None:
    """Teleport into a new worktree slot, force-updating the branch."""
    # Check if branch already has a worktree — navigate to it instead of erroring
    _navigate_to_existing_worktree(
        ctx,
        repo_root=repo.root,
        pr_number=pr_number,
        branch_name=branch_name,
        script=script,
    )

    # Fetch and force-update local branch to match remote
    _fetch_and_update_branch(ctx, repo, branch_name=branch_name, pr_number=pr_number)

    # Register with Graphite (track/retrack for all PRs, fetch base for stacked)
    _register_with_graphite(ctx, repo, branch_name=branch_name, base_ref_name=base_ref_name)

    # Create worktree slot
    worktree_path, _already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=False, force=force
    )

    post_cd_commands = ["gt submit --no-interactive"] if sync else None

    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=branch_name,
        script=script,
        command_name="pr-teleport",
        already_existed=False,
        existing_message="",
        new_message=(
            click.style("Teleported ", fg="green")
            + click.style(branch_name, fg="cyan", bold=True)
            + click.style(f" (PR #{pr_number}) into ", fg="green")
            + "{styled_path}"
        ),
        script_message_existing="",
        script_message_new=f'echo "Teleported {branch_name} (PR #{pr_number}) at $(pwd)"',
        post_cd_commands=post_cd_commands,
    )

    # Print activation instructions (non-script mode only)
    if not script:
        act_script_path = ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            act_script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=False,
        )


def _register_with_graphite(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str,
    base_ref_name: str,
) -> None:
    """Register branch with Graphite after teleport.

    Always tracks/retracks the branch when Graphite is enabled.
    For stacked PRs (base is not trunk), also fetches the base branch locally.
    """
    if not ctx.branch_manager.is_graphite_managed():
        return

    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # For stacked PRs, ensure base branch exists locally
    if base_ref_name != trunk:
        local_branches = ctx.git.branch.list_local_branches(repo.root)
        if base_ref_name not in local_branches:
            ctx.console.info(f"Fetching base branch '{base_ref_name}'...")
            ctx.git.remote.fetch_branch(repo.root, "origin", base_ref_name)
            ctx.branch_manager.create_tracking_branch(
                repo.root, base_ref_name, f"origin/{base_ref_name}"
            )

    # Always register/retrack with Graphite
    parent = ctx.branch_manager.get_parent_branch(repo.root, branch_name)
    if parent is None:
        ctx.console.info("Tracking branch with Graphite...")
        ctx.branch_manager.track_branch(repo.root, branch_name, base_ref_name)
    else:
        if ctx.graphite_branch_ops is not None:
            ctx.graphite_branch_ops.retrack_branch(repo.root, branch_name)


def _confirm_overwrite(ctx: ErkContext, *, cwd: Path, branch_name: str) -> None:
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
