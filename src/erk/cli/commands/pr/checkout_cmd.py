"""Checkout a pull request into a worktree.

This command fetches PR code and creates a worktree for local review/testing.
"""

from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
from erk.cli.commands.slot.common import (
    cleanup_worktree_artifacts,
    find_branch_assignment,
    find_inactive_slot,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
)
from erk.cli.core import worktree_path_for
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


def _allocate_slot_for_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    force: bool,
) -> Path:
    """Allocate a slot for a branch and create worktree.

    Uses the same slot allocation pattern as branch create:
    1. Check if branch is already assigned to a slot
    2. Try to reuse an inactive slot (existing worktree)
    3. Fall back to on-demand slot creation
    4. Handle pool-full with interactive/force logic

    Returns the worktree path for the allocated slot.
    Raises SystemExit(1) on failure.
    """
    ensure_erk_metadata_dir(repo)

    # Get pool size from config or default
    pool_size = get_pool_size(ctx)

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            slots=(),
            assignments=(),
        )

    # Check if branch is already assigned
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        # Branch is already assigned to a slot - just return that path
        return existing.worktree_path

    # First, prefer reusing existing worktrees (fast path)
    inactive_slot = find_inactive_slot(state, ctx.git, repo.root)
    if inactive_slot is not None:
        slot_name, worktree_path = inactive_slot
        cleanup_worktree_artifacts(worktree_path)
        ctx.git.checkout_branch(worktree_path, branch_name)
    else:
        # Fall back to on-demand slot creation
        slot_num = find_next_available_slot(state, repo.worktrees_dir)
        if slot_num is None:
            # Pool is full - handle interactively or with --force
            to_unassign = handle_pool_full_interactive(
                state, force, ctx.terminal.is_stdin_interactive()
            )
            if to_unassign is None:
                raise SystemExit(1) from None

            # Remove the assignment from state
            new_assignments = tuple(
                a for a in state.assignments if a.slot_name != to_unassign.slot_name
            )
            state = PoolState(
                version=state.version,
                pool_size=state.pool_size,
                slots=state.slots,
                assignments=new_assignments,
            )
            save_pool_state(repo.pool_json_path, state)
            user_output(
                click.style("✓ ", fg="green")
                + f"Unassigned {click.style(to_unassign.branch_name, fg='yellow')} "
                + f"from {click.style(to_unassign.slot_name, fg='cyan')}"
            )

            # Reuse the unassigned slot - worktree exists, just checkout
            slot_name = to_unassign.slot_name
            worktree_path = to_unassign.worktree_path
            cleanup_worktree_artifacts(worktree_path)
            ctx.git.checkout_branch(worktree_path, branch_name)
        else:
            # Create new slot - no worktree exists yet
            slot_name = generate_slot_name(slot_num)
            worktree_path = repo.worktrees_dir / slot_name
            worktree_path.mkdir(parents=True, exist_ok=True)
            ctx.git.add_worktree(
                repo.root,
                worktree_path,
                branch=branch_name,
                ref=None,
                create_branch=False,
            )

    # Create new assignment
    now = datetime.now(UTC).isoformat()
    new_assignment = SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=now,
        worktree_path=worktree_path,
    )

    # Update state with new assignment
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=state.slots,
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))
    return worktree_path


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("pr_reference")
@click.option("--no-slot", is_flag=True, help="Create worktree without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def pr_checkout(
    ctx: ErkContext, pr_reference: str, no_slot: bool, force: bool, script: bool
) -> None:
    """Checkout PR into a worktree for review.

    PR_REFERENCE can be a plain number (123) or GitHub URL
    (https://github.com/owner/repo/pull/123).

    Examples:

        # Checkout by PR number
        erk pr checkout 123

        # Checkout by GitHub URL
        erk pr checkout https://github.com/owner/repo/pull/123
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.feedback.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    pr_number = parse_pr_reference(pr_reference)

    # Get PR details from GitHub
    ctx.feedback.info(f"Fetching PR #{pr_number}...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        ctx.feedback.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    # Warn for closed/merged PRs
    if pr.state != "OPEN":
        ctx.feedback.info(f"Warning: PR #{pr_number} is {pr.state}")

    # Determine branch name strategy
    # For cross-repository PRs (forks), use pr/<number> to avoid conflicts
    # For same-repository PRs, use the actual branch name
    if pr.is_cross_repository:
        branch_name = f"pr/{pr_number}"
    else:
        branch_name = pr.head_ref_name

    # Check if branch already exists in a worktree
    existing_worktree = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        # Branch already exists in a worktree - activate it
        styled_path = click.style(str(existing_worktree), fg="cyan", bold=True)
        should_output = navigate_to_worktree(
            ctx,
            worktree_path=existing_worktree,
            branch=branch_name,
            script=script,
            command_name="pr-checkout",
            script_message=f'echo "Went to existing worktree for PR #{pr_number}"',
            relative_path=None,
            post_cd_commands=None,
        )
        if should_output:
            user_output(f"PR #{pr_number} already checked out at {styled_path}")
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, check if branch exists locally first
    if pr.is_cross_repository:
        # Fetch PR ref directly
        ctx.git.fetch_pr_ref(
            repo_root=repo.root, remote="origin", pr_number=pr_number, local_branch=branch_name
        )
    else:
        # Check if branch exists locally or on remote
        local_branches = ctx.git.list_local_branches(repo.root)
        if branch_name in local_branches:
            # Branch already exists locally - just need to create worktree
            pass
        else:
            # Check remote and fetch if needed
            remote_branches = ctx.git.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch_name}"
            if remote_ref in remote_branches:
                ctx.git.fetch_branch(repo.root, "origin", branch_name)
                ctx.git.create_tracking_branch(repo.root, branch_name, remote_ref)
            else:
                # Branch not on remote (maybe local-only PR?), fetch via PR ref
                ctx.git.fetch_pr_ref(
                    repo_root=repo.root,
                    remote="origin",
                    pr_number=pr_number,
                    local_branch=branch_name,
                )

    # Create worktree - use slot allocation unless --no-slot is specified
    if no_slot:
        # Old behavior: derive worktree path from branch name
        worktree_path = worktree_path_for(repo.worktrees_dir, branch_name)
        ctx.git.add_worktree(
            repo.root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        # New behavior: use slot allocation
        worktree_path = _allocate_slot_for_branch(ctx, repo, branch_name, force)

    # For stacked PRs (base is not trunk), rebase onto base branch
    # This ensures git history includes the base branch as an ancestor,
    # which `gt track` requires for proper stacking
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)
    if pr.base_ref_name != trunk_branch and not pr.is_cross_repository:
        ctx.feedback.info(f"Fetching base branch '{pr.base_ref_name}'...")
        ctx.git.fetch_branch(repo.root, "origin", pr.base_ref_name)

        ctx.feedback.info("Rebasing onto base branch...")
        rebase_result = ctx.git.rebase_onto(worktree_path, f"origin/{pr.base_ref_name}")

        if not rebase_result.success:
            ctx.git.rebase_abort(worktree_path)
            ctx.feedback.info(
                f"Warning: Rebase had conflicts. Worktree created but needs manual rebase.\n"
                f"Run: cd {worktree_path} && git rebase origin/{pr.base_ref_name}"
            )

    # Navigate to the new worktree
    styled_path = click.style(str(worktree_path), fg="cyan", bold=True)
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name="pr-checkout",
        script_message=f'echo "Checked out PR #{pr_number} at $(pwd)"',
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(f"Created worktree for PR #{pr_number} at {styled_path}")
