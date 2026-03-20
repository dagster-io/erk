"""Unified checkout command - find, switch to, or allocate a slot for a branch.

This is the primary checkout command for erk. It handles:
- Finding existing worktrees containing a branch and navigating to them
- Root worktree takeover for trunk branches
- Stack-in-place for branches checked out within an assigned slot
- Slot allocation for branches not found in any worktree
- Plan setup via --for-plan
"""

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
from erk.cli.commands.checkout_helpers import (
    display_sync_status,
    navigate_to_worktree,
    script_error_handler,
)
from erk.cli.commands.completions import complete_branch_names
from erk.cli.commands.pr.dispatch_helpers import sync_branch_to_sha
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.graphite import find_worktrees_containing_branch
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_pool import load_pool_state
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.cli_alias import alias
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.impl_folder import create_impl_folder, save_plan_ref
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import Plan, PlanNotFound
from erk_shared.plan_workflow import (
    PlanBranchSetup,
    PlanValidationFailed,
    prepare_plan_for_worktree,
)
from erk_slots.common import (
    allocate_slot_for_branch,
    find_current_slot_assignment,
    update_slot_assignment_tip,
)


def try_switch_root_worktree(ctx: ErkContext, repo: RepoContext, branch: str) -> Path | None:
    """Try to switch root worktree to branch if it's trunk and root is clean.

    This implements the "takeover" behavior where checking out trunk in a clean root
    worktree switches the root to trunk instead of creating a new dated worktree.

    Returns:
        Root worktree path if successful, None otherwise
    """
    if branch != ctx.trunk_branch:
        return None

    worktrees = ctx.git.worktree.list_worktrees(repo.root)
    root_worktree = None
    for wt in worktrees:
        if wt.is_root:
            root_worktree = wt
            break

    if root_worktree is None:
        return None

    if not ctx.git.worktree.is_worktree_clean(root_worktree.path):
        return None

    ctx.branch_manager.checkout_branch(root_worktree.path, branch)
    return root_worktree.path


def _ensure_graphite_tracking(
    ctx: ErkContext, *, repo_root: Path, target_path: Path, branch: str, script: bool
) -> None:
    """Ensure branch is tracked by Graphite (idempotent), with user confirmation."""
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        return

    trunk_branch = ctx.trunk_branch
    if trunk_branch is None:
        return

    if branch == trunk_branch:
        return

    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch in all_branches:
        return

    if script:
        return

    if not ctx.console.confirm(
        f"Branch '{branch}' is not tracked by Graphite. Track it with parent '{trunk_branch}'?",
        default=False,
    ):
        return

    ctx.branch_manager.track_branch(repo_root, branch, trunk_branch)
    user_output(f"Tracked '{branch}' with Graphite (parent: {trunk_branch})")


def _format_worktree_info(wt: WorktreeInfo, repo_root: Path) -> str:
    """Format worktree information for display."""
    current = wt.branch or "(detached HEAD)"
    if wt.path == repo_root:
        return f"  - root (currently on '{current}')"
    else:
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
    """Perform the actual checkout and switch to a worktree."""
    target_path = target_worktree.path
    current_branch_in_worktree = target_worktree.branch
    current_cwd = ctx.cwd

    effective_script = script or force_script_activation

    relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd) if worktrees else None

    need_checkout = current_branch_in_worktree != branch

    if need_checkout:
        ctx.branch_manager.checkout_branch(target_path, branch)

    _ensure_graphite_tracking(
        ctx, repo_root=repo_root, target_path=target_path, branch=branch, script=effective_script
    )

    if need_checkout and not effective_script:
        stack = ctx.branch_manager.get_branch_stack(repo_root, branch)
        if stack:
            user_output(f"Stack: {' -> '.join(stack)}")
        user_output(f"Checked out '{branch}' in worktree")

    worktree_name = target_path.name
    is_switching_location = current_cwd != target_path

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
    """Find the worktree that contains the current working directory."""
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
    """Find the root worktree from the list."""
    for wt in worktrees:
        if wt.is_root:
            return wt
    return None


def _setup_impl_for_plan(
    ctx: ErkContext,
    *,
    setup: PlanBranchSetup,
    worktree_path: Path,
    branch_name: str,
    script: bool,
) -> None:
    """Create impl folder and save plan ref after checkout for --for-plan."""
    impl_path = create_impl_folder(
        worktree_path,
        setup.plan_content,
        branch_name=branch_name,
        overwrite=True,
    )

    save_plan_ref(
        impl_path,
        provider="github",
        pr_number=str(setup.pr_number),
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
            final_message=f'echo "Prepared PR #{setup.pr_number} at $(pwd)"',
            comment="slot checkout --for-plan activation script",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name="slot-checkout",
            comment=f"slot checkout --for-plan {setup.pr_number}",
        )
        result.output_for_script_handler()
        sys.exit(0)

    user_output(f"Created .erk/impl-context/ folder from PR #{setup.pr_number}")


def _rebase_and_track_for_plan(
    ctx: ErkContext,
    *,
    repo_root: Path,
    worktree_path: Path,
    branch: str,
    parent_branch: str,
    trunk: str,
) -> None:
    """Rebase onto parent branch (if stacked) and track with Graphite."""
    if parent_branch != trunk:
        local_branches = ctx.git.branch.list_local_branches(repo_root)
        if parent_branch not in local_branches:
            user_output(f"Fetching base branch '{parent_branch}'...")
            ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
            ctx.branch_manager.create_tracking_branch(
                repo_root, parent_branch, f"origin/{parent_branch}"
            )
        else:
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
@click.option(
    "--new-slot",
    is_flag=True,
    help="Allocate a new slot instead of stacking in place",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Auto-unassign oldest branch if pool is full",
)
@script_option
@click.pass_obj
def slot_checkout(
    ctx: ErkContext,
    branch: str | None,
    for_plan: str | None,
    new_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout BRANCH by finding its worktree or allocating a slot.

    Finds which worktree has the specified branch checked out and switches to it.
    If the branch exists but isn't checked out anywhere:
    - In a slot without --new-slot: stack-in-place (update slot assignment)
    - Otherwise: allocate a new pool slot

    If the branch exists on origin but not locally, a tracking branch is created.

    Use --for-plan to resolve a PR and set up .erk/impl-context/ after checkout.

    Examples:

        erk slot co feature/user-auth      # Checkout existing worktree

        erk slot co unchecked-branch       # Allocate slot for branch

        erk slot co --for-plan 123         # Checkout PR branch with impl setup

        erk slot co feature/auth --new-slot  # Force new slot allocation

    If multiple worktrees contain the branch, all options are shown.
    """
    handler = script_error_handler(ctx) if script else contextlib.nullcontext()
    with handler:
        _slot_checkout_impl(
            ctx,
            branch=branch,
            for_plan=for_plan,
            new_slot=new_slot,
            force=force,
            script=script,
        )


def _slot_checkout_impl(
    ctx: ErkContext,
    *,
    branch: str | None,
    for_plan: str | None,
    new_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Implementation body for slot_checkout -- separated for error wrapping."""
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
        pr_number = parse_issue_identifier(for_plan)
        result = ctx.plan_store.get_managed_pr(repo.root, str(pr_number))
        if isinstance(result, PlanNotFound):
            raise click.ClickException(f"PR #{pr_number} not found")
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
    parent_branch: str | None = None
    trunk: str | None = None
    if setup is not None:
        trunk = ctx.git.branch.detect_trunk_branch(repo.root)
        if trunk is None:
            user_output("Error: Could not detect trunk branch.")
            raise SystemExit(1) from None

        local_branches = ctx.git.branch.list_local_branches(repo.root)
        branch_exists_locally = branch in local_branches

        if branch_exists_locally:
            user_output(f"Checking out PR branch: {branch}")
        else:
            ctx.git.remote.fetch_branch(repo.root, "origin", branch)
            ctx.branch_manager.create_tracking_branch(repo.root, branch, f"origin/{branch}")
            user_output(f"Created tracking branch: {branch}")

        base_ref = plan.metadata.get("base_ref_name") if plan is not None else None
        parent_branch = base_ref if isinstance(base_ref, str) else trunk

    # Get all worktrees
    worktrees = ctx.git.worktree.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Handle: branch found in worktree(s) -> navigate to it
    if len(matching_worktrees) == 1:
        target_worktree = matching_worktrees[0]

        if setup is not None:
            assert parent_branch is not None
            assert trunk is not None
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
            is_newly_created=False,
            worktrees=worktrees,
            force_script_activation=False,
        )
        return

    if len(matching_worktrees) > 1:
        # Multiple worktrees contain this branch
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            target_worktree = directly_checked_out[0]

            if setup is not None:
                assert parent_branch is not None
                assert trunk is not None
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
                is_newly_created=False,
                worktrees=worktrees,
                force_script_activation=False,
            )
            return

        if len(directly_checked_out) == 0:
            user_output(
                f"Error: Internal state mismatch. Branch '{branch}' was allocated "
                f"but no worktree has it checked out.\n"
                f"This may indicate corrupted pool state."
            )
            raise SystemExit(1)

        # Multiple worktrees have it directly checked out
        user_output(f"Branch '{branch}' exists in multiple worktrees:")
        for wt in matching_worktrees:
            user_output(_format_worktree_info(wt, repo.root))
        user_output("\nPlease specify which worktree to use.")
        raise SystemExit(1)

    # Branch not found in any worktree -- decide what to do

    # Verify branch exists (if not --for-plan, which already handled it)
    if setup is None:
        local_branches = ctx.git.branch.list_local_branches(repo.root)
        if branch not in local_branches:
            remote_branches = ctx.git.branch.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch}"
            if remote_ref in remote_branches:
                user_output(
                    f"Branch '{branch}' exists on origin, creating local tracking branch..."
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

    # Try switching clean root worktree if checking out trunk
    root_path = try_switch_root_worktree(ctx, repo, branch)
    if root_path is not None:
        worktrees = ctx.git.worktree.list_worktrees(repo.root)
        matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)
        if len(matching_worktrees) == 1:
            _perform_checkout(
                ctx,
                repo_root=repo.root,
                target_worktree=matching_worktrees[0],
                branch=branch,
                script=script,
                is_newly_created=False,
                worktrees=worktrees,
                force_script_activation=False,
            )
            return

    # Stack-in-place: if in a slot and not --new-slot, update assignment tip
    if not new_slot:
        state = load_pool_state(repo.pool_json_path)
        if state is not None:
            current_assignment = find_current_slot_assignment(state, repo.root)
            if current_assignment is not None:
                slot_result = update_slot_assignment_tip(
                    repo.pool_json_path,
                    state,
                    current_assignment,
                    branch_name=branch,
                    now=ctx.time.now().isoformat(),
                )
                target_wt = WorktreeInfo(path=slot_result.worktree_path, branch=branch)

                if setup is not None:
                    assert parent_branch is not None
                    assert trunk is not None
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

    # Allocate a new slot for the branch
    slot_result = allocate_slot_for_branch(
        ctx,
        repo,
        branch,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )

    target_wt = WorktreeInfo(path=slot_result.worktree_path, branch=branch)

    if setup is not None:
        assert parent_branch is not None
        assert trunk is not None
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
        is_newly_created=not slot_result.already_assigned,
        worktrees=worktrees,
        force_script_activation=True,
    )
