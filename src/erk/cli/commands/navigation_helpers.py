import os
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
    render_activation_script,
)
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.debug import debug_log
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import machine_output, user_output
from erk_shared.scratch.markers import PENDING_LEARN_MARKER, marker_exists


def check_pending_learn_marker(worktree_path: Path, force: bool) -> None:
    """Check for pending learn marker and block deletion if present.

    This provides friction before worktree deletion to ensure insights are
    extracted from the session logs. The marker is created by `erk pr land`
    and deleted by `erk plan learn raw`.

    Args:
        worktree_path: Path to the worktree being deleted
        force: If True, warn but don't block deletion

    Raises:
        SystemExit: If marker exists and force is False
    """
    if not marker_exists(worktree_path, PENDING_LEARN_MARKER):
        return

    if force:
        user_output(
            click.style("Warning: ", fg="yellow") + "Skipping pending learn (--force used).\n"
        )
        return

    user_output(
        click.style("Error: ", fg="red") + "Worktree has pending learn.\n"
        "Run: erk plan learn raw\n"
        "Or use --force to skip learn."
    )
    raise SystemExit(1)


def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    Ensure.invariant(
        not ctx.git.has_uncommitted_changes(ctx.cwd),
        "Cannot delete current branch with uncommitted changes.\n"
        "Please commit or stash your changes first.",
    )


def verify_pr_closed_or_merged(ctx: ErkContext, repo_root: Path, branch: str, force: bool) -> None:
    """Verify that the branch's PR is closed or merged on GitHub.

    Warns if no PR exists, raises SystemExit if PR is still OPEN (unless force=True).
    Allows deletion for both MERGED and CLOSED PRs (abandoned/rejected work).

    Args:
        ctx: Erk context
        repo_root: Path to the repository root
        branch: Branch name to check
        force: If True, prompt for confirmation instead of blocking on open PRs
    """
    pr_details = ctx.github.get_pr_for_branch(repo_root, branch)

    if isinstance(pr_details, PRNotFound):
        # Warn but continue when no PR exists
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"No pull request found for branch '{branch}'.\n"
            "Proceeding with deletion without PR verification."
        )
        return  # Allow deletion to proceed

    if pr_details.state == "OPEN":
        if force:
            # Show warning and prompt for confirmation
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Pull request for branch '{branch}' is still open.\n"
                + f"{pr_details.url}"
            )
            if not ctx.console.confirm("Delete branch anyway?", default=False):
                raise SystemExit(1)
            # Ask if user wants to close the PR
            if ctx.console.confirm("Close the PR?", default=True):
                ctx.github.close_pr(repo_root, pr_details.number)
                user_output(f"✓ Closed PR #{pr_details.number}")
            return  # User confirmed, allow deletion

        # Block deletion for open PRs (active work in progress)
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is still open.\n"
            + f"{pr_details.url}\n"
            + "Only closed or merged branches can be deleted with --delete-current.\n"
            + "Use -f/--force to delete anyway."
        )
        raise SystemExit(1)


def validate_for_deletion(
    *,
    ctx: ErkContext,
    repo_root: Path,
    current_branch: str,
    worktree_path: Path,
    force: bool,
) -> None:
    """Run all safety checks before deletion.

    This consolidates the validation logic shared by up.py and down.py
    when using --delete-current flag.

    Args:
        ctx: Erk context
        repo_root: Path to the repository root
        current_branch: Name of the branch being deleted
        worktree_path: Path to the worktree being deleted
        force: If True, prompts instead of blocking on open PRs

    Raises:
        SystemExit: If any validation check fails
    """
    check_clean_working_tree(ctx)
    verify_pr_closed_or_merged(ctx, repo_root, current_branch, force)
    check_pending_learn_marker(worktree_path, force)


def delete_branch_and_worktree(
    ctx: ErkContext, repo: RepoContext, branch: str, worktree_path: Path
) -> None:
    """Delete the specified branch and its worktree.

    Uses two-step deletion: git worktree remove, then branch delete.
    Note: remove_worktree already calls prune internally, so no additional prune needed.

    Args:
        ctx: Erk context
        repo: Repository context (uses main_repo_root for safe directory operations)
        branch: Branch name to delete
        worktree_path: Path to the worktree to remove
    """
    # Use main_repo_root (not repo.root) to ensure we escape to a directory that
    # still exists after worktree removal. repo.root equals the worktree path when
    # running from inside a worktree.
    # main_repo_root is always set by RepoContext.__post_init__, but ty doesn't know
    main_repo = repo.main_repo_root if repo.main_repo_root else repo.root

    # Escape the worktree if we're inside it (prevents FileNotFoundError after removal)
    # Both paths must be resolved for reliable comparison - Path.cwd() returns resolved path
    # but worktree_path may not be resolved, causing equality check to fail for same directory
    cwd = Path.cwd().resolve()
    resolved_worktree = worktree_path.resolve()
    if cwd == resolved_worktree or resolved_worktree in cwd.parents:
        os.chdir(main_repo)

    # Remove the worktree (already calls prune internally)
    ctx.git.worktree.remove_worktree(main_repo, worktree_path, force=True)
    user_output(f"✓ Removed worktree: {click.style(str(worktree_path), fg='green')}")

    # Delete the branch using BranchManager abstraction (respects use_graphite config)
    ctx.branch_manager.delete_branch(main_repo, branch)
    user_output(f"✓ Deleted branch: {click.style(branch, fg='yellow')}")


def find_assignment_by_worktree_path(
    state: PoolState, worktree_path: Path
) -> SlotAssignment | None:
    """Find a slot assignment by its worktree path.

    Args:
        state: Current pool state
        worktree_path: Path to the worktree to find

    Returns:
        SlotAssignment if the worktree is a pool slot, None otherwise
    """
    if not worktree_path.exists():
        return None
    resolved_path = worktree_path.resolve()
    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        if assignment.worktree_path.resolve() == resolved_path:
            return assignment
    return None


def get_slot_name_for_worktree(pool_json_path: Path, worktree_path: Path) -> str | None:
    """Get the slot name if the worktree is a pool slot.

    Args:
        pool_json_path: Path to the pool.json file
        worktree_path: Path to the worktree to check

    Returns:
        Slot name if the worktree is a pool slot, None otherwise
    """
    state = load_pool_state(pool_json_path)
    if state is None:
        return None
    assignment = find_assignment_by_worktree_path(state, worktree_path)
    if assignment is None:
        return None
    return assignment.slot_name


def render_deferred_deletion_commands(
    *,
    worktree_path: Path,
    branch: str,
    slot_name: str | None,
    is_graphite_managed: bool,
    main_repo_root: Path,
) -> list[str]:
    """Generate shell commands for deferred worktree/branch deletion.

    These commands are embedded in the activation script's post_cd_commands,
    so the deletion only happens when the user sources the activation script.
    This makes the deletion atomic with the navigation.

    Args:
        worktree_path: Path to the worktree to delete
        branch: Branch name to delete
        slot_name: Slot name if the worktree is a pool slot, None otherwise
        is_graphite_managed: Whether to use Graphite (gt) or plain Git for branch deletion
        main_repo_root: Path to the main repository root (for operations after worktree removal)

    Returns:
        List of shell commands to execute for deferred deletion
    """
    commands: list[str] = []
    quoted_main_repo = shlex.quote(str(main_repo_root))

    # Worktree cleanup
    if slot_name is not None:
        commands.append(f"erk slot unassign {shlex.quote(slot_name)}")
    else:
        commands.append(f"git worktree remove --force {shlex.quote(str(worktree_path))}")

    # Branch deletion (run from main repo root to ensure it exists after worktree removal)
    quoted_branch = shlex.quote(branch)
    if is_graphite_managed:
        # Use gt delete to clean up Graphite metadata
        commands.append(f"gt delete -f {quoted_branch}")
    else:
        commands.append(f"git -C {quoted_main_repo} branch -D {quoted_branch}")

    return commands


def unallocate_worktree_and_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
    worktree_path: Path,
) -> None:
    """Unallocate a worktree and delete its branch.

    If worktree is a pool slot: unassigns slot (keeps directory for reuse), deletes branch.
    If not a pool slot: removes worktree directory, deletes branch.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        branch: Branch name to delete
        worktree_path: Path to the worktree to unallocate
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Check if this is a slot worktree
    state = load_pool_state(repo.pool_json_path)
    assignment: SlotAssignment | None = None
    if state is not None:
        assignment = find_assignment_by_worktree_path(state, worktree_path)

    if assignment is not None:
        # Slot worktree: unassign instead of delete
        # state is guaranteed to be non-None since assignment was found in it
        assert state is not None
        execute_unassign(ctx, repo, state, assignment)
        ctx.branch_manager.delete_branch(main_repo_root, branch)
        user_output(click.style("✓", fg="green") + " Unassigned slot and deleted branch")
    else:
        # Non-slot worktree: delete both
        ctx.git.worktree.remove_worktree(main_repo_root, worktree_path, force=True)
        ctx.branch_manager.delete_branch(main_repo_root, branch)
        user_output(click.style("✓", fg="green") + " Removed worktree and deleted branch")


def activate_target(
    *,
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
    is_root: bool,
) -> NoReturn:
    """Activate a worktree or root repository and exit.

    This is the unified activation function for both worktrees and root repos.
    The is_root parameter determines the messaging.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree/root directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)
        preserve_relative_path: If True, compute and preserve the user's
            relative directory position from the current worktree
        post_cd_commands: Optional shell commands to run after activation (e.g., entry scripts)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.
        is_root: If True, uses root repo messaging; otherwise uses worktree messaging

    Raises:
        SystemExit: Always raises (either success or error)
    """
    Ensure.path_exists(ctx, target_path, f"Target not found: {target_path}")

    target_name = target_path.name

    # Compute relative path to preserve user's position within worktree
    relative_path: Path | None = None
    if preserve_relative_path:
        worktrees = ctx.git.worktree.list_worktrees(repo.root)
        relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    # Determine messaging based on whether this is root or a worktree
    if is_root:
        final_message = 'echo "Went to root repo: $(pwd)"'
        script_comment = "work activate-script (root repo)"
        activate_comment = "activate root"
    else:
        final_message = 'echo "Activated worktree: $(pwd)"'
        script_comment = "work activate-script"
        activate_comment = f"activate {target_name}"

    if script:
        activation_script = render_activation_script(
            worktree_path=target_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message=final_message,
            comment=script_comment,
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=activate_comment,
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {result.path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {result.path.exists()}")

        result.output_for_shell_integration()
    else:
        script_path = ensure_worktree_activate_script(
            worktree_path=target_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            script_path,
            source_branch=source_branch,
            force=force,
            config=activation_config_activate_only(),
            copy=True,
        )
    raise SystemExit(0)


def activate_worktree(
    *,
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
) -> NoReturn:
    """Activate a worktree and exit.

    This is a convenience wrapper around activate_target() for worktrees.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)
        preserve_relative_path: If True (default), compute and preserve the user's
            relative directory position from the current worktree
        post_cd_commands: Optional shell commands to run after activation (e.g., entry scripts)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.

    Raises:
        SystemExit: Always raises (either success or error)
    """
    activate_target(
        ctx=ctx,
        repo=repo,
        target_path=target_path,
        script=script,
        command_name=command_name,
        preserve_relative_path=preserve_relative_path,
        post_cd_commands=post_cd_commands,
        source_branch=source_branch,
        force=force,
        is_root=False,
    )


def activate_root_repo(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    command_name: str,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
) -> NoReturn:
    """Activate the root repository and exit.

    This is a convenience wrapper around activate_target() for root repos.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)
        post_cd_commands: Optional shell commands to run after cd (e.g., git pull)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.

    Raises:
        SystemExit: Always raises (either success or error)
    """
    # Use main_repo_root (not repo.root) to ensure we reference a directory that
    # still exists after worktree removal. repo.root equals the worktree path when
    # running from inside a worktree.
    root_path = repo.main_repo_root if repo.main_repo_root else repo.root

    activate_target(
        ctx=ctx,
        repo=repo,
        target_path=root_path,
        script=script,
        command_name=command_name,
        preserve_relative_path=True,
        post_cd_commands=post_cd_commands,
        source_branch=source_branch,
        force=force,
        is_root=True,
    )


def resolve_up_navigation(
    ctx: ErkContext, repo: RepoContext, current_branch: str, worktrees: list[WorktreeInfo]
) -> tuple[str, bool]:
    """Resolve --up navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.worktree.list_worktrees()

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at top of stack)
    """
    # Navigate up to child branch
    children = Ensure.truthy(
        ctx.branch_manager.get_child_branches(repo.root, current_branch),
        "Already at the top of the stack (no child branches)",
    )

    # Fail explicitly if multiple children exist
    children_list = ", ".join(f"'{c}'" for c in children)
    Ensure.invariant(
        len(children) <= 1,
        f"Branch '{current_branch}' has multiple children: {children_list}.\n"
        f"Please create worktree for specific child: erk create <branch-name>",
    )

    # Use the single child
    target_branch = children[0]

    # Check if target branch has a worktree, create if necessary
    target_wt_path = ctx.git.worktree.find_worktree_for_branch(repo.root, target_branch)
    if target_wt_path is None:
        # Auto-create worktree for target branch
        _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, target_branch)
        return target_branch, was_created

    return target_branch, False


def resolve_down_navigation(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    current_branch: str,
    worktrees: list[WorktreeInfo],
    trunk_branch: str | None,
) -> tuple[str, bool]:
    """Resolve --down navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.worktree.list_worktrees()
        trunk_branch: Configured trunk branch name, or None for auto-detection

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name or 'root' to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at bottom of stack)
    """
    # Navigate down to parent branch
    parent_branch = ctx.branch_manager.get_parent_branch(repo.root, current_branch)
    if parent_branch is None:
        # Check if we're already on trunk
        detected_trunk = ctx.git.detect_trunk_branch(repo.root)
        Ensure.invariant(
            current_branch != detected_trunk,
            f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')",
        )
        # Not on trunk but no parent - keep as direct error (no clear condition to express)
        user_output(
            click.style("Error: ", fg="red")
            + "Could not determine parent branch from Graphite metadata"
        )
        raise SystemExit(1)

    # Check if parent is the trunk - if so, switch to root
    detected_trunk = ctx.git.detect_trunk_branch(repo.root)
    if parent_branch == detected_trunk:
        # Check if trunk is checked out in root (repo.root path)
        trunk_wt_path = ctx.git.worktree.find_worktree_for_branch(repo.root, detected_trunk)
        if trunk_wt_path is not None and trunk_wt_path == repo.root:
            # Trunk is in root repository, not in a dedicated worktree
            return "root", False
        else:
            # Trunk has a dedicated worktree
            if trunk_wt_path is None:
                # Auto-create worktree for trunk branch
                _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
                return parent_branch, was_created
            return parent_branch, False
    else:
        # Parent is not trunk, check if it has a worktree
        target_wt_path = ctx.git.worktree.find_worktree_for_branch(repo.root, parent_branch)
        if target_wt_path is None:
            # Auto-create worktree for parent branch
            _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
            return parent_branch, was_created
        return parent_branch, False


@dataclass(frozen=True)
class NavigationResult:
    """Result of navigation resolution."""

    target_path: Path
    target_name: str
    was_created: bool
    is_root: bool


def execute_stack_navigation(
    *,
    ctx: ErkContext,
    direction: Literal["up", "down"],
    script: bool,
    delete_current: bool,
    force: bool,
) -> NoReturn:
    """Unified navigation for up/down commands with --delete-current support.

    This is the main orchestrator for stack navigation that consolidates
    the logic from up.py and down.py into a single function.

    Phases:
    1. Validate preconditions (gh authenticated)
    2. Resolve navigation target (direction-specific)
    3. If delete_current: validate + prepare deferred deletion commands
    4. Activate target (script or interactive mode)

    Args:
        ctx: Erk context
        direction: Navigation direction ("up" or "down")
        script: Whether to output script path for shell integration
        delete_current: If True, delete current branch/worktree after navigation
        force: If True, prompts instead of blocking on validation failures

    Raises:
        SystemExit: Always exits with 0 on success or 1 on error
    """
    from erk.cli.core import discover_repo_context

    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    # Get all worktrees
    worktrees = ctx.git.worktree.list_worktrees(repo.root)

    # Direction-specific validation for --delete-current
    if direction == "up" and delete_current:
        children = ctx.branch_manager.get_child_branches(repo.root, current_branch)
        Ensure.invariant(
            len(children) > 0,
            "Cannot navigate up: already at top of stack. "
            "Use 'gt branch delete' to delete this branch",
        )
        Ensure.invariant(
            len(children) <= 1,
            "Cannot navigate up: multiple child branches exist. "
            "Use 'gt up' to interactively select a branch",
        )

    # Store current worktree path for deletion (before navigation)
    current_worktree_path: Path | None = None
    if delete_current:
        current_worktree_path = Ensure.not_none(
            ctx.git.worktree.find_worktree_for_branch(repo.root, current_branch),
            f"Could not find worktree for branch '{current_branch}'",
        )

        # Run all safety checks
        validate_for_deletion(
            ctx=ctx,
            repo_root=repo.root,
            current_branch=current_branch,
            worktree_path=current_worktree_path,
            force=force,
        )

    # Resolve navigation target (direction-specific)
    if direction == "up":
        target_name, was_created = resolve_up_navigation(ctx, repo, current_branch, worktrees)
        is_root = False
    else:  # direction == "down"
        target_name, was_created = resolve_down_navigation(
            ctx,
            repo=repo,
            current_branch=current_branch,
            worktrees=worktrees,
            trunk_branch=ctx.trunk_branch,
        )
        is_root = target_name == "root"

    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )

    # Prepare deferred deletion commands if --delete-current is set
    deletion_commands: list[str] | None = None
    if delete_current and current_worktree_path is not None:
        main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
        slot_name = get_slot_name_for_worktree(repo.pool_json_path, current_worktree_path)
        use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
        deletion_commands = render_deferred_deletion_commands(
            worktree_path=current_worktree_path,
            branch=current_branch,
            slot_name=slot_name,
            is_graphite_managed=use_graphite,
            main_repo_root=main_repo_root,
        )

    # Resolve target path
    if is_root:
        target_path = repo.main_repo_root if repo.main_repo_root else repo.root
    else:
        target_path = Ensure.not_none(
            ctx.git.worktree.find_worktree_for_branch(repo.root, target_name),
            f"Branch '{target_name}' has no worktree. This should not happen.",
        )

    # Handle activation
    if delete_current and current_worktree_path is not None:
        # Handle activation inline with deferred deletion
        _activate_with_deferred_deletion(
            ctx=ctx,
            repo=repo,
            target_path=target_path,
            worktrees=worktrees,
            deletion_commands=deletion_commands,
            script=script,
            command_name=direction,
            current_branch=current_branch,
            force=force,
            is_root=is_root,
        )
    else:
        # No cleanup needed, use standard activation
        activate_target(
            ctx=ctx,
            repo=repo,
            target_path=target_path,
            script=script,
            command_name=direction,
            preserve_relative_path=True,
            post_cd_commands=None,
            source_branch=current_branch,
            force=force,
            is_root=is_root,
        )


def _activate_with_deferred_deletion(
    *,
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    worktrees: list[WorktreeInfo],
    deletion_commands: list[str] | None,
    script: bool,
    command_name: str,
    current_branch: str,
    force: bool,
    is_root: bool,
) -> NoReturn:
    """Handle activation with deferred deletion commands embedded in script.

    This is an internal helper for execute_stack_navigation() that handles
    the --delete-current path where deletion is deferred to script sourcing.

    Args:
        ctx: Erk context
        repo: Repository context
        target_path: Path to the target worktree/root
        worktrees: List of worktrees for relative path computation
        deletion_commands: Shell commands to run after activation for deferred deletion
        script: Whether to output script path for shell integration
        command_name: Name of the command (for script generation)
        current_branch: Branch being navigated away from
        force: If True and current_branch is provided, shows delete hint
        is_root: If True, uses root repo messaging

    Raises:
        SystemExit: Always exits with 0 on success
    """
    Ensure.path_exists(ctx, target_path, f"Target not found: {target_path}")

    # Determine messaging
    if is_root:
        final_message = 'echo "Went to root repo: $(pwd)"'
        script_comment = "work activate-script (root repo)"
        activate_comment = "activate root"
    else:
        final_message = 'echo "Activated worktree: $(pwd)"'
        script_comment = "work activate-script"
        activate_comment = f"activate {target_path.name}"

    if script:
        activation_script = render_activation_script(
            worktree_path=target_path,
            target_subpath=compute_relative_path_in_worktree(worktrees, ctx.cwd),
            post_cd_commands=deletion_commands,
            final_message=final_message,
            comment=script_comment,
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=activate_comment,
        )
        machine_output(str(result.path), nl=False)
    else:
        script_path = ensure_worktree_activate_script(
            worktree_path=target_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            script_path,
            source_branch=current_branch,
            force=force,
            config=activation_config_activate_only(),
            copy=True,
        )

    # Deletion is deferred to script sourcing - no immediate cleanup
    raise SystemExit(0)
