"""Command to start a planning session in an assigned pool slot.

This command assigns a pool slot and launches Claude for planning,
without requiring a pre-existing plan file or GitHub issue.
"""

from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.slot.common import (
    allocate_slot_for_branch,
    find_branch_assignment,
    find_inactive_slot,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
)
from erk.cli.commands.wt.create_cmd import run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import PoolState, load_pool_state
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.naming import sanitize_worktree_name
from erk_shared.output.output import user_output


def _generate_timestamp_name() -> str:
    """Generate a timestamp-based branch name for planning.

    Returns:
        Branch name like "planning-01-04-0930"
    """
    now = datetime.now(tz=UTC)
    return f"planning-{now.strftime('%m-%d-%H%M')}"


def _determine_base_branch(ctx: ErkContext, repo_root: Path) -> str:
    """Determine the base branch for new worktree creation.

    When Graphite is enabled and the user is on a non-trunk branch,
    stack on the current branch. Otherwise, use trunk.

    Args:
        ctx: Erk context
        repo_root: Repository root path

    Returns:
        Base branch name to use as ref for worktree creation
    """
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    if not use_graphite:
        return trunk_branch

    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch and current_branch != trunk_branch:
        return current_branch

    return trunk_branch


def _build_claude_command(dangerous: bool, model: str | None) -> str:
    """Build a Claude CLI invocation without a slash command.

    Args:
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

    Returns:
        Complete Claude CLI command string
    """
    cmd = "claude --permission-mode acceptEdits"
    if dangerous:
        cmd += " --dangerously-skip-permissions"
    if model is not None:
        cmd += f" --model {model}"
    return cmd


@click.command("start", cls=CommandWithHiddenOptions)
@click.option(
    "-n",
    "--name",
    type=str,
    help="Branch name for the planning session (auto-generated if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be executed without doing it",
)
@click.option(
    "--dangerous",
    is_flag=True,
    help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
)
@script_option
@click.option(
    "-m",
    "--model",
    type=str,
    help="Model to use for Claude (haiku/h, sonnet/s, opus/o)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Auto-unassign oldest slot if pool is full (no interactive prompt).",
)
@click.pass_obj
def plan_start(
    ctx: ErkContext,
    *,
    name: str | None,
    dry_run: bool,
    dangerous: bool,
    script: bool,
    model: str | None,
    force: bool,
) -> None:
    """Start a planning session in an assigned pool slot.

    This command assigns a pool slot, creates a planning branch, and launches
    Claude for planning. Use this when you want to explore a problem space
    before committing to a specific plan.

    If --name is provided, it will be used as the branch name (sanitized).
    Otherwise, a timestamp-based name like "planning-01-04-0930" is generated.

    Examples:

    \b
      # Start planning with auto-generated branch name
      erk plan start

    \b
      # Start planning with a custom branch name
      erk plan start --name my-feature

    \b
      # Skip permission prompts
      erk plan start --dangerous

    \b
      # Shell integration
      source <(erk plan start --script)

    \b
      # With specific model
      erk plan start --model opus
    """
    # Normalize model name (validates and expands aliases)
    model = normalize_model_name(model)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Determine base branch (respects worktree stacking)
    base_branch = _determine_base_branch(ctx, repo_root)

    # Generate or sanitize branch name
    if name is not None:
        branch = sanitize_worktree_name(name)
    else:
        branch = _generate_timestamp_name()

    ctx.console.info(f"Planning branch: {branch}")

    # Get pool size from config
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
    elif state.pool_size != pool_size:
        # Update pool_size from config if it changed
        state = PoolState(
            version=state.version,
            pool_size=pool_size,
            slots=state.slots,
            assignments=state.assignments,
        )

    # Check if branch is already assigned to a slot
    existing_assignment = find_branch_assignment(state, branch)
    if existing_assignment is not None:
        # Branch already has a slot - use it
        slot_name = existing_assignment.slot_name
        wt_path = existing_assignment.worktree_path
        ctx.console.info(f"Branch '{branch}' already assigned to {slot_name}")

        # Handle dry-run mode
        if dry_run:
            _show_dry_run_output(slot_name, branch, dangerous, model)
            return

        # Execute planning session
        _execute_planning(
            ctx,
            repo_root=repo_root,
            wt_path=wt_path,
            branch=branch,
            dangerous=dangerous,
            model=model,
            script=script,
        )
        return

    # Check if branch already exists locally
    local_branches = ctx.git.list_local_branches(repo_root)
    use_existing_branch = branch in local_branches

    # Find available slot (preview for dry-run mode)
    inactive_slot = find_inactive_slot(state, ctx.git, repo_root)
    if inactive_slot is not None:
        slot_name_preview, _ = inactive_slot
    else:
        slot_num = find_next_available_slot(state, repo.worktrees_dir)
        if slot_num is not None:
            slot_name_preview = generate_slot_name(slot_num)
        else:
            # Pool is full - slot name will be determined after unassigning
            # For dry-run, just show "oldest slot"
            slot_name_preview = "(oldest slot after unassign)"

    # Handle dry-run mode
    if dry_run:
        _show_dry_run_output(slot_name_preview, branch, dangerous, model)
        return

    # Create branch if needed (BEFORE slot allocation)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_existing_branch:
        ctx.console.info(f"Creating branch '{branch}' from {base_branch}...")
        ctx.git.create_branch(repo_root, branch, base_branch)
        if use_graphite:
            ctx.graphite.track_branch(repo_root, branch, base_branch)

    # Allocate slot for the branch (branch now exists)
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )
    slot_name = result.slot_name
    wt_path = result.worktree_path

    ctx.console.success(f"✓ Assigned {branch} to {slot_name}")

    # Load local config for post-worktree setup
    config = ctx.local_config if ctx.local_config is not None else LoadedConfig.test()

    # Run post-worktree setup
    run_post_worktree_setup(
        ctx, config=config, worktree_path=wt_path, repo_root=repo_root, name=slot_name
    )

    # Execute planning session
    _execute_planning(
        ctx,
        repo_root=repo_root,
        wt_path=wt_path,
        branch=branch,
        dangerous=dangerous,
        model=model,
        script=script,
    )


def _show_dry_run_output(
    slot_name: str,
    branch: str,
    dangerous: bool,
    model: str | None,
) -> None:
    """Show dry-run output for slot assignment."""
    dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
    user_output(dry_run_header + " No changes will be made\n")

    user_output(f"Would assign to slot '{slot_name}'")
    user_output(f"  Branch: {branch}")

    user_output("\nWould launch Claude:")
    claude_cmd = _build_claude_command(dangerous, model)
    user_output(f"  {claude_cmd}")


def _execute_planning(
    ctx: ErkContext,
    *,
    repo_root: Path,
    wt_path: Path,
    branch: str,
    dangerous: bool,
    model: str | None,
    script: bool,
) -> None:
    """Execute planning session - script mode or interactive.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        wt_path: Worktree path
        branch: Branch name
        dangerous: Whether to skip permission prompts
        model: Optional model name
        script: Whether to output shell script instead of launching Claude
    """
    if script:
        # Script mode - output activation script
        _output_activation_script(
            ctx, wt_path=wt_path, branch=branch, dangerous=dangerous, model=model
        )
    else:
        # Interactive mode - launch Claude
        _launch_claude_interactive(
            ctx, repo_root=repo_root, wt_path=wt_path, dangerous=dangerous, model=model
        )


def _output_activation_script(
    ctx: ErkContext, *, wt_path: Path, branch: str, dangerous: bool, model: str | None
) -> None:
    """Output activation script for shell integration.

    Args:
        ctx: Erk context
        wt_path: Worktree path
        branch: Branch name (for comment)
        dangerous: Whether to skip permission prompts
        model: Optional model name
    """
    # Build Claude command (no slash command)
    claude_cmd = _build_claude_command(dangerous, model)

    # Get base activation script (cd + venv + env)
    full_script = render_activation_script(
        worktree_path=wt_path,
        target_subpath=None,
        post_cd_commands=None,
        final_message=claude_cmd,
        comment=f"plan start {branch}",
    )

    result = ctx.script_writer.write_activation_script(
        full_script,
        command_name="plan-start",
        comment=f"activate {wt_path.name} and launch Claude for planning",
    )

    result.output_for_shell_integration()


def _launch_claude_interactive(
    ctx: ErkContext, *, repo_root: Path, wt_path: Path, dangerous: bool, model: str | None
) -> None:
    """Launch Claude in interactive mode for planning.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        wt_path: Worktree path
        dangerous: Whether to skip permission prompts
        model: Optional model name

    Note:
        This function never returns in production - the process is replaced by Claude
    """
    click.echo("Entering interactive planning mode...", err=True)
    try:
        # Launch Claude without a slash command (empty string)
        # The executor handles empty command by not appending it to args
        ctx.claude_executor.execute_interactive(
            worktree_path=wt_path,
            dangerous=dangerous,
            command="",  # No slash command - user will drive the planning session
            target_subpath=compute_relative_path_in_worktree(
                ctx.git.list_worktrees(repo_root), ctx.cwd
            ),
            model=model,
        )
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
