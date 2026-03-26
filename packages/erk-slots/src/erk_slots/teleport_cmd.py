"""Teleport a PR's remote state to the local branch.

Remote-first counterpart to 'checkout'. While checkout preserves local state
(reusing existing worktrees, keeping unpushed commits), teleport force-resets
the local branch to match the remote exactly. Use teleport when a remote agent
has pushed commits and you want your local copy to match.

Automatically ensures the branch has a worktree slot, allocating one if needed.
"""

from contextlib import nullcontext
from dataclasses import dataclass
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
)
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.core.script_error import script_error_handler
from erk_shared.gateway.github.types import PRNotFound
from erk_slots.common import find_assignment_by_worktree, update_slot_assignment_tip


@dataclass(frozen=True)
class TeleportPlan:
    """Describes what a teleport operation will do, without executing it."""

    pr_number: int
    branch_name: str
    base_ref_name: str
    ahead: int
    behind: int
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    already_had_worktree: bool
    worktree_path: Path
    branch_exists_locally: bool
    is_graphite_managed: bool
    trunk: str
    sync: bool
    has_slot: bool


@click.command("teleport", cls=CommandWithHiddenOptions)
@click.argument("pr_number", type=int)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--sync", is_flag=True, help="Run gt submit after teleport to sync with Graphite")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@script_option
@click.pass_obj
def slot_teleport(
    ctx: ErkContext,
    pr_number: int,
    force: bool,
    sync: bool,
    dry_run: bool,
    script: bool,
) -> None:
    """Teleport a PR's remote state to local, overwriting local branch.

    Unlike 'checkout' which preserves local state (reusing existing worktrees
    and keeping local commits), teleport is remote-first: it force-resets the
    local branch to match the remote exactly, discarding any local commits
    that haven't been pushed.

    Automatically ensures the branch has a worktree slot, allocating one if
    the branch is not already in any worktree.

    \b
    Use 'checkout' when you want to start working on a PR locally.
    Use 'teleport' when a remote agent has pushed new commits and you
    want your local branch to match the remote exactly.

    \b
    Beyond gh pr checkout:
        - Force-resets local branch to match remote (requires confirmation;
          use -f to skip)
        - Worktree pool integration (navigates to existing worktrees, creates
          slot and updates assignments)
        - Graphite integration (when configured: tracks/retracks branch,
          fetches base for stacked PRs; --sync runs gt submit after
          teleport)
        - Shell activation scripts (--script mode for cmux)
        - --dry-run previews what would happen without making changes

    \b
    Examples:
        erk slot teleport 123              # Teleport PR #123 to its worktree slot
        erk slot teleport 123 -f           # Skip confirmation
        erk slot teleport 123 --script --sync  # Full setup with Graphite sync
        erk slot teleport 123 --dry-run    # Preview what would be lost
    """
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Dry-run forces human-readable output (no script mode)
    if dry_run:
        script = False

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

        # Build plan (what would happen)
        teleport_plan = _build_teleport_plan(
            ctx,
            repo,
            pr_number=pr_number,
            branch_name=branch_name,
            base_ref_name=base_ref_name,
            sync=sync,
            script=script,
        )

        # Decide: display or execute
        if dry_run:
            _display_dry_run_report(teleport_plan)
            raise SystemExit(0)

        _execute_teleport(ctx, repo, plan=teleport_plan, force=force, script=script)


def _build_teleport_plan(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    branch_name: str,
    base_ref_name: str,
    sync: bool,
    script: bool,
) -> TeleportPlan:
    """Build a TeleportPlan (pre-checks + plan building).

    Ensures the branch has a worktree slot, allocating one if needed.
    May exit early via SystemExit(0) if the branch is already in sync.
    """
    cwd = ctx.cwd
    current_branch = ctx.git.branch.get_current_branch(cwd)

    # Check if branch is already in a worktree
    existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)

    # Determine if we're operating in-place (branch already has a home):
    # - branch is the current branch in this worktree, OR
    # - branch is checked out in another worktree
    if existing_worktree is not None:
        already_had_worktree = True
        worktree_path = existing_worktree
    elif current_branch == branch_name:
        # We're on the branch in the current worktree (not tracked in worktree list)
        already_had_worktree = True
        worktree_path = cwd
    else:
        # Branch not in any worktree — will allocate a slot
        already_had_worktree = False
        worktree_path = cwd

    # Fetch latest remote state
    ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)

    # Compute divergence
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    branch_exists_locally = branch_name in local_branches

    ahead, behind = 0, 0
    if branch_exists_locally and already_had_worktree:
        # Only check divergence for in-place operations
        try:
            ahead, behind = ctx.git.branch.get_ahead_behind(worktree_path, branch_name)
        except RuntimeError:
            pass

        if ahead == 0 and behind == 0:
            ctx.console.info("Branch is already in sync with remote. Nothing to teleport.")
            raise SystemExit(0)

    # Gather state for plan
    staged, modified, untracked = ctx.git.status.get_file_status(worktree_path)
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)
    is_graphite_managed = ctx.branch_manager.is_graphite_managed()

    # Check slot assignment
    state = load_pool_state(repo.pool_json_path)
    has_slot = False
    if state is not None:
        has_slot = find_assignment_by_worktree(state, ctx.git, worktree_path) is not None

    return TeleportPlan(
        pr_number=pr_number,
        branch_name=branch_name,
        base_ref_name=base_ref_name,
        ahead=ahead,
        behind=behind,
        staged=staged,
        modified=modified,
        untracked=untracked,
        already_had_worktree=already_had_worktree,
        worktree_path=worktree_path,
        branch_exists_locally=branch_exists_locally,
        is_graphite_managed=is_graphite_managed,
        trunk=trunk,
        sync=sync,
        has_slot=has_slot,
    )


def _execute_teleport(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    plan: TeleportPlan,
    force: bool,
    script: bool,
) -> None:
    """Execute the mutations for a teleport.

    If the branch was not already in a worktree, allocates a slot first
    and navigates to it. Force-resets the branch to match remote in all cases.
    """
    # If branch needs a new worktree, allocate a slot first
    if not plan.already_had_worktree:
        worktree_path, _already_existed = ensure_branch_has_worktree(
            ctx, repo, branch_name=plan.branch_name, no_slot=False, force=force
        )
    else:
        worktree_path = plan.worktree_path
        # Show divergence info and confirm overwrite (only for in-place, not new slot)
        if plan.branch_exists_locally and not force:
            _confirm_overwrite(ctx, cwd=worktree_path, branch_name=plan.branch_name)

    # Force-reset local branch to match remote
    ctx.git.branch.create_branch(
        repo.root, plan.branch_name, f"origin/{plan.branch_name}", force=True
    )

    # Reset working tree to match the new branch head
    ctx.git.branch.checkout_branch(worktree_path, plan.branch_name)

    # Slot awareness: update assignment if in a managed slot
    state = load_pool_state(repo.pool_json_path)
    if state is not None:
        current_assignment = find_assignment_by_worktree(state, ctx.git, worktree_path)
        if current_assignment is not None:
            update_slot_assignment_tip(
                repo.pool_json_path,
                state,
                current_assignment,
                branch_name=plan.branch_name,
                now=ctx.time.now().isoformat(),
            )

    # Register with Graphite (track/retrack for all PRs, fetch base for stacked)
    _register_with_graphite(
        ctx, repo, branch_name=plan.branch_name, base_ref_name=plan.base_ref_name
    )

    post_cd_commands = ["gt submit --no-interactive"] if plan.sync else None

    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=plan.branch_name,
        script=script,
        command_name="pr-teleport",
        already_existed=False,
        existing_message="",
        new_message=(
            click.style("Teleported ", fg="green")
            + click.style(plan.branch_name, fg="cyan", bold=True)
            + click.style(f" to match remote (PR #{plan.pr_number}) at ", fg="green")
            + "{styled_path}"
        ),
        script_message_existing="",
        script_message_new=(
            f'echo "Teleported {plan.branch_name} to match remote (PR #{plan.pr_number})"'
        ),
        post_cd_commands=post_cd_commands,
    )

    # Print activation instructions when navigating to a new slot (non-script mode only)
    if not plan.already_had_worktree and not script:
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


def _display_dry_run_report(plan: TeleportPlan) -> None:
    """Display a dry-run report showing what teleport would do."""
    click.echo(f"\nDry run: erk slot teleport {plan.pr_number}")

    # Local state section (only for in-place when there's something to report)
    has_local_state = plan.ahead > 0 or plan.staged or plan.modified or plan.untracked
    if has_local_state:
        click.echo(click.style("\n  Local state that would be discarded:", bold=True))
        if plan.ahead > 0:
            msg = f"    {plan.ahead} local commit(s) ahead of remote (would be lost)"
            click.echo(click.style(msg, fg="yellow"))
        if plan.staged:
            file_list = ", ".join(plan.staged[:5])
            suffix = f" (+{len(plan.staged) - 5} more)" if len(plan.staged) > 5 else ""
            click.echo(f"    {len(plan.staged)} staged file(s): {file_list}{suffix}")
        if plan.modified:
            file_list = ", ".join(plan.modified[:5])
            suffix = f" (+{len(plan.modified) - 5} more)" if len(plan.modified) > 5 else ""
            click.echo(f"    {len(plan.modified)} modified file(s): {file_list}{suffix}")
        if plan.untracked:
            click.echo(f"    {len(plan.untracked)} untracked file(s)")

    # Operations section
    click.echo(click.style("\n  Operations:", bold=True))
    click.echo(f"    Would fetch origin/{plan.branch_name}")

    if not plan.already_had_worktree:
        click.echo("    Would allocate new worktree slot")
    else:
        click.echo(f"    Would force-reset '{plan.branch_name}' to match remote")
        click.echo(f"    Would checkout '{plan.branch_name}'")
        if plan.has_slot:
            click.echo("    Would update slot assignment")

    if plan.is_graphite_managed:
        if plan.base_ref_name != plan.trunk:
            click.echo(f"    Would fetch base branch '{plan.base_ref_name}'")
        click.echo(f"    Would track branch with Graphite (base: {plan.base_ref_name})")

    if plan.sync:
        click.echo("    Would run gt submit --no-interactive")

    click.echo(click.style("\n[DRY RUN] No changes made", fg="yellow"))


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
