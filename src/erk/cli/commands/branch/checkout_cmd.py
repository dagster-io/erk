"""Checkout command - find and switch to a worktree by branch name."""

import contextlib
import sys
from pathlib import Path

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
    render_activation_script,
)
from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import (
    display_sync_status,
    navigate_to_worktree,
    script_error_handler,
)
from erk.cli.commands.completions import complete_branch_names
from erk.cli.commands.pr.dispatch_helpers import sync_branch_to_sha
from erk.cli.commands.slot.common import (
    allocate_slot_for_branch,
    update_slot_assignment_tip,
)
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.graphite import find_worktrees_containing_branch
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.impl_folder import create_impl_folder, save_plan_ref
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan, PlanNotFound
from erk_shared.plan_workflow import (
    PlanBranchSetup,
    PlanValidationFailed,
    prepare_plan_for_worktree,
)


def try_switch_root_worktree(ctx: ErkContext, repo: RepoContext, branch: str) -> Path | None:
    """Try to switch root worktree to branch if it's trunk and root is clean.

    This implements the "takeover" behavior where checking out trunk in a clean root
    worktree switches the root to trunk instead of creating a new dated worktree.

    Args:
        ctx: Erk context with git operations
        repo: Repository context
        branch: Branch name to check

    Returns:
        Root worktree path if successful, None otherwise
    """
    # Check if branch is trunk
    if branch != ctx.trunk_branch:
        return None

    # Find root worktree
    worktrees = ctx.git.worktree.list_worktrees(repo.root)
    root_worktree = None
    for wt in worktrees:
        if wt.is_root:
            root_worktree = wt
            break

    if root_worktree is None:
        return None

    # Check if root is clean
    if not ctx.git.worktree.is_worktree_clean(root_worktree.path):
        return None

    # Switch root to trunk branch
    ctx.branch_manager.checkout_branch(root_worktree.path, branch)

    return root_worktree.path


def _ensure_graphite_tracking(
    ctx: ErkContext, *, repo_root: Path, target_path: Path, branch: str, script: bool
) -> None:
    """Ensure branch is tracked by Graphite (idempotent), with user confirmation.

    If the branch is not already tracked, prompts the user and tracks it with
    trunk as parent if confirmed. This enables branches created without Graphite
    (e.g., via erk-queue) to be managed with Graphite locally.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_path: Worktree path where `gt track` should run
        branch: Target branch name
        script: Whether to output only the activation script
    """
    # Skip if Graphite is disabled
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        return

    trunk_branch = ctx.trunk_branch
    # Skip if no trunk branch detected (shouldn't happen in checkout context)
    if trunk_branch is None:
        return

    # Skip trunk branch - it's always implicitly tracked
    if branch == trunk_branch:
        return

    # Check if already tracked (LBYL)
    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch in all_branches:
        return  # Already tracked, nothing to do

    # In script mode, skip tracking (no interactive prompts allowed)
    if script:
        return

    # Prompt user for confirmation
    if not ctx.console.confirm(
        f"Branch '{branch}' is not tracked by Graphite. Track it with parent '{trunk_branch}'?",
        default=False,
    ):
        return

    # Track the branch with trunk as parent
    ctx.branch_manager.track_branch(repo_root, branch, trunk_branch)
    user_output(f"Tracked '{branch}' with Graphite (parent: {trunk_branch})")


def _format_worktree_info(wt: WorktreeInfo, repo_root: Path) -> str:
    """Format worktree information for display.

    Args:
        wt: WorktreeInfo to format
        repo_root: Path to repository root (used to identify root worktree)

    Returns:
        Formatted string like "root (currently on 'main')" or "wt-name (currently on 'feature')"
    """
    current = wt.branch or "(detached HEAD)"
    if wt.path == repo_root:
        return f"  - root (currently on '{current}')"
    else:
        # Get worktree name from path
        wt_name = wt.path.name
        return f"  - {wt_name} (currently on '{current}')"


def _perform_checkout(
    ctx: ErkContext,
    *,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
    is_newly_created: bool,
    worktrees: list[WorktreeInfo] | None,
    force_script_activation: bool,
) -> None:
    """Perform the actual checkout and switch to a worktree.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_worktree: The worktree to switch to
        branch: Target branch name
        script: Whether to output only the activation script
        is_newly_created: Whether the worktree was just created
        worktrees: Optional list of worktrees (for relative path computation)
        force_script_activation: Whether to force script mode output (e.g. for stack-in-place)
    """
    target_path = target_worktree.path
    current_branch_in_worktree = target_worktree.branch
    current_cwd = ctx.cwd

    # In stack-in-place, we always emit the activation script even if the user
    # didn't pass --script, so shell integration can pick it up automatically.
    effective_script = script or force_script_activation

    # Compute relative path to preserve directory position
    relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd) if worktrees else None

    # Check if branch is already checked out in the worktree
    need_checkout = current_branch_in_worktree != branch

    # If we need to checkout, do it before generating the activation script
    if need_checkout:
        ctx.branch_manager.checkout_branch(target_path, branch)

    # Ensure branch is tracked with Graphite (idempotent)
    _ensure_graphite_tracking(
        ctx, repo_root=repo_root, target_path=target_path, branch=branch, script=effective_script
    )

    if need_checkout and not effective_script:
        # Show stack context in non-script mode
        stack = ctx.branch_manager.get_branch_stack(repo_root, branch)
        if stack:
            user_output(f"Stack: {' -> '.join(stack)}")
        user_output(f"Checked out '{branch}' in worktree")

    # Compute four-case message for script and user output
    worktree_name = target_path.name
    is_switching_location = current_cwd != target_path

    # Generate styled script message (used for script mode and as basis for user output)
    styled_wt = click.style(worktree_name, fg="cyan", bold=True)
    styled_branch = click.style(branch, fg="yellow")

    if is_newly_created:
        script_message = f'echo "Switched to new worktree {styled_wt}"'
        user_message = f"Switched to new worktree {styled_wt}"
    elif not is_switching_location:
        script_message = f'echo "Already on branch {styled_branch} in worktree {styled_wt}"'
        user_message = f"Already on branch {styled_branch} in worktree {styled_wt}"
    elif not need_checkout:
        if worktree_name == branch:
            script_message = f'echo "Switched to worktree {styled_wt}"'
            user_message = f"Switched to worktree {styled_wt}"
        else:
            script_message = f'echo "Switched to worktree {styled_wt} (branch {styled_branch})"'
            user_message = f"Switched to worktree {styled_wt} (branch {styled_branch})"
    else:
        script_message = (
            f'echo "Switched to worktree {styled_wt} and checked out branch {styled_branch}"'
        )
        user_message = f"Switched to worktree {styled_wt} and checked out branch {styled_branch}"

    # Use consolidated navigation function
    should_output_message = navigate_to_worktree(
        ctx,
        worktree_path=target_path,
        branch=branch,
        script=effective_script,
        command_name="checkout",
        script_message=script_message,
        relative_path=relative_path,
        post_cd_commands=None,
    )

    if should_output_message:
        user_output(user_message)
        display_sync_status(ctx, worktree_path=target_path, branch=branch, script=script)

        # Print activation instructions for opt-in workflow
        activation_script_path = ensure_worktree_activate_script(
            worktree_path=target_path,
            post_create_commands=None,
        )
        same_worktree = target_path.resolve() == ctx.cwd.resolve()
        print_activation_instructions(
            activation_script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=same_worktree,
        )


def _find_containing_worktree(worktrees: list[WorktreeInfo], cwd: Path) -> WorktreeInfo | None:
    """Find the worktree that contains the current working directory.

    Resolves paths and checks if cwd is under a worktree path. Returns the root
    worktree as fallback if no other worktree contains cwd.

    Args:
        worktrees: List of all worktrees
        cwd: Current working directory

    Returns:
        WorktreeInfo containing cwd, or root worktree as fallback, or None if empty list
    """
    if not cwd.exists():
        return _find_root_worktree(worktrees)

    resolved_cwd = cwd.resolve()
    for wt in worktrees:
        if wt.path.exists():
            resolved_wt = wt.path.resolve()
            if resolved_cwd == resolved_wt or resolved_cwd.is_relative_to(resolved_wt):
                return wt

    return _find_root_worktree(worktrees)


def _find_root_worktree(worktrees: list[WorktreeInfo]) -> WorktreeInfo | None:
    """Find the root worktree from the list.

    Args:
        worktrees: List of all worktrees

    Returns:
        Root worktree if found, None otherwise
    """
    for wt in worktrees:
        if wt.is_root:
            return wt
    return None


def _find_current_slot_assignment(state: PoolState, cwd: Path) -> SlotAssignment | None:
    """Find slot assignment matching the current working directory.

    Inlined to avoid circular import from navigation_helpers.

    Args:
        state: Current pool state
        cwd: Current working directory path

    Returns:
        SlotAssignment if cwd is a pool slot, None otherwise
    """
    if not cwd.exists():
        return None
    resolved_path = cwd.resolve()
    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        if assignment.worktree_path.resolve() == resolved_path:
            return assignment
    return None


def _setup_impl_for_plan(
    ctx: ErkContext,
    *,
    setup: PlanBranchSetup,
    worktree_path: Path,
    branch_name: str,
    script: bool,
) -> None:
    """Create impl folder and save plan ref after checkout for --for-plan.

    In script mode, outputs an activation script and exits. In normal mode,
    prints a confirmation message.

    Args:
        ctx: Erk context
        setup: Plan setup info from prepare_plan_for_worktree
        worktree_path: Path to the target worktree
        branch_name: Git branch name for scoping the impl directory
        script: Whether to output only the activation script
    """
    impl_path = create_impl_folder(
        worktree_path,
        setup.plan_content,
        branch_name=branch_name,
        overwrite=True,
    )

    save_plan_ref(
        impl_path,
        provider="github",
        plan_id=str(setup.plan_number),
        url=setup.issue_url,
        labels=(),
        objective_id=setup.objective_issue,
        node_ids=None,
    )

    if script:
        activation_script = render_activation_script(
            worktree_path=worktree_path,
            target_subpath=None,
            post_cd_commands=None,
            final_message=f'echo "Prepared PR #{setup.plan_number} at $(pwd)"',
            comment="erk branch checkout --for-plan activation script",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name="branch-checkout",
            comment=f"branch checkout --for-plan {setup.plan_number}",
        )
        result.output_for_script_handler()
        sys.exit(0)

    user_output(f"Created .erk/impl-context/ folder from PR #{setup.plan_number}")


def _rebase_and_track_for_plan(
    ctx: ErkContext,
    *,
    repo_root: Path,
    worktree_path: Path,
    branch: str,
    parent_branch: str,
    trunk: str,
) -> None:
    """Rebase onto parent branch (if stacked) and track with Graphite.

    For stacked plans where parent_branch != trunk, the parent may have advanced
    since the plan was saved. Rebasing ensures git history includes the parent's
    tip, which gt track requires for proper stacking.

    Mirrors the pattern from pr/checkout_cmd.py for stacked PRs.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        worktree_path: Path to the worktree (used as cwd for rebase)
        branch: The plan branch name
        parent_branch: The parent branch to rebase onto and track with
        trunk: The trunk branch name
    """
    # For stacked plans (parent is not trunk), rebase onto parent first
    if parent_branch != trunk:
        # Ensure parent branch is up to date locally
        local_branches = ctx.git.branch.list_local_branches(repo_root)
        if parent_branch not in local_branches:
            user_output(f"Fetching base branch '{parent_branch}'...")
            ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
            ctx.branch_manager.create_tracking_branch(
                repo_root, parent_branch, f"origin/{parent_branch}"
            )
        else:
            # Parent exists locally but may be stale after squash/rebase.
            # Update to match origin so gt track sees consistent history.
            ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
            remote_sha = ctx.git.branch.get_branch_head(repo_root, f"origin/{parent_branch}")
            local_sha = ctx.git.branch.get_branch_head(repo_root, parent_branch)
            if remote_sha is not None and remote_sha != local_sha:
                sync_branch_to_sha(ctx, repo_root, parent_branch, remote_sha)

        user_output("Rebasing onto base branch...")
        rebase_result = ctx.git.rebase.rebase_onto(worktree_path, f"origin/{parent_branch}")

        if not rebase_result.success:
            ctx.git.rebase.rebase_abort(worktree_path)
            user_output(
                f"Warning: Rebase had conflicts. Worktree created but needs manual rebase.\n"
                f"Run: cd {worktree_path} && git rebase origin/{parent_branch}"
            )

    ctx.branch_manager.track_branch(repo_root, branch, parent_branch)


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch", metavar="BRANCH", required=False, shell_complete=complete_branch_names)
@click.option(
    "--for-plan",
    "for_plan",
    type=str,
    default=None,
    help="PR number or URL with erk-pr label",
)
@click.option("--no-slot", is_flag=True, help="Create worktree without slot assignment")
@click.option(
    "--new-slot",
    is_flag=True,
    help="Allocate a new slot for the branch (default: checkout in current worktree)",
)
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def branch_checkout(
    ctx: ErkContext,
    branch: str | None,
    for_plan: str | None,
    no_slot: bool,
    new_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout BRANCH by finding and switching to its worktree.

    Prints the activation path for the target worktree.

    This command finds which worktree has the specified branch checked out
    and switches to it. If the branch exists but isn't checked out anywhere,
    a worktree is automatically created. If the branch exists on origin but
    not locally, a tracking branch and worktree are created automatically.

    Use --for-plan to resolve a PR and set up .erk/impl-context/ after checkout.

    Examples:

        erk br co feature/user-auth      # Checkout existing worktree

        erk br co unchecked-branch       # Auto-create worktree

        erk br co --for-plan 123         # Checkout PR branch with .erk/impl-context/ setup

    If multiple worktrees contain the branch, all options are shown.
    """
    handler = script_error_handler(ctx) if script else contextlib.nullcontext()
    with handler:
        _branch_checkout_impl(
            ctx,
            branch=branch,
            for_plan=for_plan,
            no_slot=no_slot,
            new_slot=new_slot,
            force=force,
            script=script,
        )


def _branch_checkout_impl(
    ctx: ErkContext,
    *,
    branch: str | None,
    for_plan: str | None,
    no_slot: bool,
    new_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Implementation body for branch_checkout — separated for error wrapping."""
    # Mutual exclusivity validation
    if for_plan is not None and branch is not None:
        user_output(
            "Error: Cannot specify both BRANCH and --for-plan.\n"
            "Use --for-plan to derive branch name from PR, or provide BRANCH directly."
        )
        raise SystemExit(1) from None

    if for_plan is None and branch is None:
        user_output("Error: Must provide BRANCH argument or --for-plan option.")
        raise SystemExit(1) from None

    if new_slot and no_slot:
        user_output("Error: --new-slot and --no-slot cannot be used together.")
        raise SystemExit(1) from None

    # Use existing repo from context if available (for tests), otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Plan setup - fetches plan and derives branch name if --for-plan is used
    setup: PlanBranchSetup | None = None
    plan: Plan | None = None

    if for_plan is not None:
        plan_number = parse_issue_identifier(for_plan)
        result = ctx.plan_store.get_plan(repo.root, str(plan_number))
        if isinstance(result, PlanNotFound):
            raise click.ClickException(f"PR #{plan_number} not found")
        plan = result

        plan_result = prepare_plan_for_worktree(plan, ctx.time.now(), warn_non_open=True)
        if isinstance(plan_result, PlanValidationFailed):
            user_output(f"Error: {plan_result.message}")
            raise SystemExit(1) from None

        setup = plan_result
        branch = setup.branch_name

        for warning in setup.warnings:
            user_output(click.style("Warning: ", fg="yellow") + warning)

    # At this point, branch is guaranteed to be set
    assert branch is not None

    # If --for-plan, handle branch creation/tracking before checkout
    if setup is not None:
        trunk = ctx.git.branch.detect_trunk_branch(repo.root)
        if trunk is None:
            user_output("Error: Could not detect trunk branch.")
            raise SystemExit(1) from None

        local_branches = ctx.git.branch.list_local_branches(repo.root)
        branch_exists_locally = branch in local_branches

        # Plan branch was created by plan-save
        if branch_exists_locally:
            user_output(f"Checking out PR branch: {branch}")
        else:
            ctx.git.remote.fetch_branch(repo.root, "origin", branch)
            ctx.branch_manager.create_tracking_branch(repo.root, branch, f"origin/{branch}")
            user_output(f"Created tracking branch: {branch}")
        # Use base_ref_name from plan metadata (set by plan-save via the draft PR)
        # to determine the correct Graphite parent, instead of guessing from current branch
        base_ref = plan.metadata.get("base_ref_name") if plan is not None else None
        parent_branch = base_ref if isinstance(base_ref, str) else trunk
        # Defer track_branch until after worktree is created — for stacked plans
        # (parent != trunk), we need to rebase first so gt track succeeds

    # Get all worktrees
    worktrees = ctx.git.worktree.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Track whether we're creating a new worktree
    is_newly_created = False

    # Handle three cases: no match, one match, multiple matches
    if len(matching_worktrees) == 0:
        # No worktrees have this branch checked out
        # First, try switching clean root worktree if checking out trunk
        root_path = try_switch_root_worktree(ctx, repo, branch)
        if root_path is not None:
            # Successfully switched root to trunk - refresh and jump to it
            worktrees = ctx.git.worktree.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)
        else:
            # Root not available or not trunk - auto-create worktree
            if no_slot:
                # Legacy behavior: branch-name-based paths
                _worktree_path, is_newly_created = ensure_worktree_for_branch(
                    ctx, repo, branch, is_plan_derived=False
                )
            else:
                # New behavior: slot allocation
                # First check if this is the trunk branch - trunk cannot have a slot
                trunk_branch = ctx.git.branch.detect_trunk_branch(repo.root)
                if branch == trunk_branch:
                    user_output(
                        f'Error: Cannot create worktree for trunk branch "{trunk_branch}".\n'
                        f"The trunk branch should be checked out in the root worktree.\n"
                        f"To switch to {trunk_branch}, use:\n"
                        f"  erk br co root"
                    )
                    raise SystemExit(1) from None

                # Ensure branch exists (may need to create tracking branch)
                # Skip if --for-plan already handled branch creation
                if setup is None:
                    local_branches = ctx.git.branch.list_local_branches(repo.root)
                    if branch not in local_branches:
                        remote_branches = ctx.git.branch.list_remote_branches(repo.root)
                        remote_ref = f"origin/{branch}"
                        if remote_ref in remote_branches:
                            user_output(
                                f"Branch '{branch}' exists on origin,"
                                " creating local tracking branch..."
                            )
                            ctx.git.remote.fetch_branch(repo.root, "origin", branch)
                            ctx.branch_manager.create_tracking_branch(repo.root, branch, remote_ref)
                        else:
                            user_output(
                                f"Error: Branch '{branch}' does not exist.\n"
                                f"To create a new branch and worktree, run:\n"
                                f"  erk wt create --branch {branch}"
                            )
                            raise SystemExit(1) from None

                # Detect if running in an assigned slot (for stack-in-place)
                # Unless --new-slot forces a new allocation
                state = load_pool_state(repo.pool_json_path)
                current_assignment = None
                if state is not None and not new_slot:
                    current_assignment = _find_current_slot_assignment(state, repo.root)

                if current_assignment is not None:
                    # Stack in place — update assignment to new tip, no new slot
                    assert state is not None
                    slot_result = update_slot_assignment_tip(
                        repo.pool_json_path,
                        state,
                        current_assignment,
                        branch_name=branch,
                        now=ctx.time.now().isoformat(),
                    )
                    user_output(
                        click.style(
                            f"✓ Stacked {branch} in {slot_result.slot_name} (in place)", fg="green"
                        )
                    )

                    # Checkout the branch before _setup_impl_for_plan, which may
                    # sys.exit(0) in script mode and skip _perform_checkout.
                    ctx.branch_manager.checkout_branch(slot_result.worktree_path, branch)

                    # Build a synthetic WorktreeInfo for the existing worktree.
                    # Branch is already checked out above.
                    target_wt = WorktreeInfo(
                        path=slot_result.worktree_path,
                        branch=branch,
                    )

                    if setup is not None:
                        _rebase_and_track_for_plan(
                            ctx,
                            repo_root=repo.root,
                            worktree_path=target_wt.path,
                            branch=branch,
                            parent_branch=parent_branch,
                            trunk=trunk,
                        )
                        _setup_impl_for_plan(
                            ctx,
                            setup=setup,
                            worktree_path=target_wt.path,
                            branch_name=branch,
                            script=script,
                        )

                    worktrees = ctx.git.worktree.list_worktrees(repo.root)
                    _perform_checkout(
                        ctx,
                        repo_root=repo.root,
                        target_worktree=target_wt,
                        branch=branch,
                        script=script,
                        is_newly_created=False,
                        worktrees=worktrees,
                        force_script_activation=True,
                    )
                    return
                elif new_slot:
                    # Allocate slot for the branch (only with explicit --new-slot)
                    slot_result = allocate_slot_for_branch(
                        ctx,
                        repo,
                        branch,
                        force=force,
                        reuse_inactive_slots=True,
                        cleanup_artifacts=True,
                    )
                    is_newly_created = not slot_result.already_assigned
                    if is_newly_created:
                        msg = f"✓ Assigned {branch} to {slot_result.slot_name}"
                        user_output(click.style(msg, fg="green"))
                else:
                    # Default: checkout in current worktree (like git checkout)
                    current_wt = _find_containing_worktree(worktrees, ctx.cwd)
                    wt_path = current_wt.path if current_wt is not None else repo.root
                    ctx.branch_manager.checkout_branch(wt_path, branch)
                    target_wt = WorktreeInfo(path=wt_path, branch=branch)

                    if setup is not None:
                        _rebase_and_track_for_plan(
                            ctx,
                            repo_root=repo.root,
                            worktree_path=target_wt.path,
                            branch=branch,
                            parent_branch=parent_branch,
                            trunk=trunk,
                        )
                        _setup_impl_for_plan(
                            ctx,
                            setup=setup,
                            worktree_path=target_wt.path,
                            branch_name=branch,
                            script=script,
                        )

                    worktrees = ctx.git.worktree.list_worktrees(repo.root)
                    _perform_checkout(
                        ctx,
                        repo_root=repo.root,
                        target_worktree=target_wt,
                        branch=branch,
                        script=script,
                        is_newly_created=False,
                        worktrees=worktrees,
                        force_script_activation=True,
                    )
                    return

            # Refresh worktree list to include the newly created worktree
            worktrees = ctx.git.worktree.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

        # Fall through to jump to the worktree

    if len(matching_worktrees) == 1:
        # --new-slot was requested but the branch already existed in a worktree
        # (not one we just created in the len==0 branch above)
        if new_slot and not is_newly_created:
            raise click.ClickException(
                f"Branch '{branch}' is already checked out in {matching_worktrees[0].path.name}. "
                f"Cannot create a new slot for an existing branch."
            )

        # Exactly one worktree contains this branch
        target_worktree = matching_worktrees[0]

        # Set up impl folder if --for-plan was used
        if setup is not None:
            _rebase_and_track_for_plan(
                ctx,
                repo_root=repo.root,
                worktree_path=target_worktree.path,
                branch=branch,
                parent_branch=parent_branch,
                trunk=trunk,
            )
            _setup_impl_for_plan(
                ctx,
                setup=setup,
                worktree_path=target_worktree.path,
                branch_name=branch,
                script=script,
            )

        _perform_checkout(
            ctx,
            repo_root=repo.root,
            target_worktree=target_worktree,
            branch=branch,
            script=script,
            is_newly_created=is_newly_created,
            worktrees=worktrees,
            force_script_activation=False,
        )

    else:
        # Multiple worktrees contain this branch
        if new_slot:
            raise click.ClickException(
                f"Branch '{branch}' is already checked out in multiple worktrees. "
                f"Cannot create a new slot for an existing branch."
            )

        # Check if any worktree has the branch directly checked out
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            # Exactly one worktree has the branch directly checked out - jump to it
            target_worktree = directly_checked_out[0]

            # Set up impl folder if --for-plan was used
            if setup is not None:
                _rebase_and_track_for_plan(
                    ctx,
                    repo_root=repo.root,
                    worktree_path=target_worktree.path,
                    branch=branch,
                    parent_branch=parent_branch,
                    trunk=trunk,
                )
                _setup_impl_for_plan(
                    ctx,
                    setup=setup,
                    worktree_path=target_worktree.path,
                    branch_name=branch,
                    script=script,
                )

            _perform_checkout(
                ctx,
                repo_root=repo.root,
                target_worktree=target_worktree,
                branch=branch,
                script=script,
                is_newly_created=is_newly_created,
                worktrees=worktrees,
                force_script_activation=False,
            )
        elif len(directly_checked_out) == 0:
            # Branch was allocated but no worktree has it checked out
            # This indicates stale pool state
            user_output(
                f"Error: Internal state mismatch. Branch '{branch}' was allocated "
                f"but no worktree has it checked out.\n"
                f"This may indicate corrupted pool state."
            )
            raise SystemExit(1)
        else:
            # Multiple worktrees have it directly checked out
            user_output(f"Branch '{branch}' exists in multiple worktrees:")
            for wt in matching_worktrees:
                user_output(_format_worktree_info(wt, repo.root))

            user_output("\nPlease specify which worktree to use.")
            raise SystemExit(1)
