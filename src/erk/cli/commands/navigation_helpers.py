from pathlib import Path

import click
from erk_shared.debug import debug_log
from erk_shared.git.abc import WorktreeInfo
from erk_shared.output.output import machine_output, user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


def ensure_graphite_enabled(ctx: ErkContext) -> None:
    """Validate that Graphite is enabled.

    Args:
        ctx: Erk context

    Raises:
        SystemExit: If Graphite is not enabled
    """
    Ensure.invariant(
        ctx.global_config is not None and ctx.global_config.use_graphite,
        "This command requires Graphite to be enabled. Run 'erk config set use_graphite true'",
    )


def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    Ensure.invariant(
        not ctx.git.has_uncommitted_changes(ctx.cwd),
        "Cannot delete current branch with uncommitted changes.\n"
        "Please commit or stash your changes first.",
    )


def verify_pr_closed_or_merged(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Verify that the branch's PR is closed or merged on GitHub.

    Warns if no PR exists, raises SystemExit if PR is still OPEN.
    Allows deletion for both MERGED and CLOSED PRs (abandoned/rejected work).
    """
    pr_info = ctx.github.get_pr_status(repo_root, branch, debug=False)

    if pr_info.state == "NONE" or pr_info.pr_number is None:
        # Warn but continue when no PR exists
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"No pull request found for branch '{branch}'.\n"
            "Proceeding with deletion without PR verification."
        )
        return  # Allow deletion to proceed

    if pr_info.state == "OPEN":
        # Block deletion for open PRs (active work in progress)
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is still open.\n"
            "Only closed or merged branches can be deleted with --delete-current."
        )
        raise SystemExit(1)


def delete_branch_and_worktree(
    ctx: ErkContext, repo_root: Path, branch: str, worktree_path: Path
) -> None:
    """Delete the specified branch and its worktree.

    Uses two-step deletion: git worktree remove, then manual cleanup.
    """

    # Remove the worktree
    ctx.git.remove_worktree(repo_root, worktree_path, force=True)
    user_output(f"✓ Removed worktree: {click.style(str(worktree_path), fg='green')}")

    # Delete the branch using Git abstraction
    ctx.git.delete_branch_with_graphite(repo_root, branch, force=True)
    user_output(f"✓ Deleted branch: {click.style(branch, fg='yellow')}")

    # Prune worktree metadata
    ctx.git.prune_worktrees(repo_root)


def activate_root_repo(ctx: ErkContext, repo: RepoContext, script: bool, command_name: str) -> None:
    """Activate the root repository and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)

    Raises:
        SystemExit: Always (successful exit after activation)
    """
    root_path = repo.root
    if script:
        script_content = render_activation_script(
            worktree_path=root_path,
            final_message='echo "Went to root repo: $(pwd)"',
            comment="work activate-script (root repo)",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name=command_name,
            comment="activate root",
        )
        machine_output(str(result.path), nl=False)
    else:
        user_output(f"Went to root repo: {root_path}")
        user_output(
            "\nShell integration not detected. "
            "Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"Or use: source <(erk {command_name} --script)")
    raise SystemExit(0)


def activate_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
) -> None:
    """Activate a worktree and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)

    Raises:
        SystemExit: If worktree not found, or after successful activation
    """
    wt_path = target_path

    Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")

    worktree_name = wt_path.name

    if script:
        activation_script = render_activation_script(worktree_path=wt_path)
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=f"activate {worktree_name}",
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {result.path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {result.path.exists()}")

        result.output_for_shell_integration()
    else:
        user_output(
            "Shell integration not detected. Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"\nOr use: source <(erk {command_name} --script)")
    raise SystemExit(0)


def resolve_up_navigation(
    ctx: ErkContext, repo: RepoContext, current_branch: str, worktrees: list[WorktreeInfo]
) -> tuple[str, bool]:
    """Resolve --up navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at top of stack)
    """
    # Navigate up to child branch
    children = Ensure.truthy(
        ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch),
        "Already at the top of the stack (no child branches)",
    )

    # Fail explicitly if multiple children exist
    if len(children) > 1:
        children_list = ", ".join(f"'{child}'" for child in children)
        user_output(
            f"Error: Branch '{current_branch}' has multiple children: {children_list}.\n"
            f"Please create worktree for specific child: erk create <branch-name>"
        )
        raise SystemExit(1)

    # Use the single child
    target_branch = children[0]

    # Check if target branch has a worktree, create if necessary
    target_wt_path = ctx.git.find_worktree_for_branch(repo.root, target_branch)
    if target_wt_path is None:
        # Auto-create worktree for target branch
        _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, target_branch)
        return target_branch, was_created

    return target_branch, False


def resolve_down_navigation(
    ctx: ErkContext,
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
        worktrees: List of worktrees from git_ops.list_worktrees()
        trunk_branch: Configured trunk branch name, or None for auto-detection

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name or 'root' to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at bottom of stack)
    """
    # Navigate down to parent branch
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is None:
        # Check if we're already on trunk
        detected_trunk = ctx.git.detect_default_branch(repo.root, trunk_branch)
        if current_branch == detected_trunk:
            user_output(f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')")
            raise SystemExit(1)
        else:
            user_output("Error: Could not determine parent branch from Graphite metadata")
            raise SystemExit(1)

    # Check if parent is the trunk - if so, switch to root
    detected_trunk = ctx.git.detect_default_branch(repo.root, trunk_branch)
    if parent_branch == detected_trunk:
        # Check if trunk is checked out in root (repo.root path)
        trunk_wt_path = ctx.git.find_worktree_for_branch(repo.root, detected_trunk)
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
        target_wt_path = ctx.git.find_worktree_for_branch(repo.root, parent_branch)
        if target_wt_path is None:
            # Auto-create worktree for parent branch
            _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
            return parent_branch, was_created
        return parent_branch, False
