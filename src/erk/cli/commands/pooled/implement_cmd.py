"""Pooled implement command - assign issue to pool slot and implement.

This command combines:
1. Pool slot assignment (like pooled assign)
2. Plan setup (creates .impl/ folder)
3. Claude execution (like implement)

The key difference from `erk implement` is that instead of creating a new worktree,
it assigns the issue's branch to an existing pool slot worktree.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.commands.implement_shared import (
    PlanSource,
    build_claude_args,
    build_command_sequence,
    detect_target_type,
    execute_interactive_mode,
    execute_non_interactive_mode,
    implement_common_options,
    normalize_model_name,
    output_activation_instructions,
    prepare_plan_source_from_issue,
    validate_flags,
)
from erk.cli.commands.pooled.common import (
    find_branch_assignment,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
)
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.output.output import user_output


def _assign_branch_to_slot(
    ctx: ErkContext,
    *,
    repo_root: Path,
    worktrees_dir: Path,
    pool_json_path: Path,
    branch_name: str,
    force: bool,
) -> Path:
    """Assign a branch to an available pool slot, creating branch if needed.

    This reuses the pool slot assignment logic from pooled assign,
    but handles the case where the branch doesn't exist yet (creates it from trunk).

    Args:
        ctx: Erk context
        repo_root: Repository root path
        worktrees_dir: Directory for worktrees
        pool_json_path: Path to pool.json
        branch_name: Branch name to assign
        force: Whether to auto-unassign oldest slot if pool is full

    Returns:
        Path to the assigned worktree slot

    Raises:
        SystemExit: If assignment fails (pool full without --force, etc.)
    """
    pool_size = get_pool_size(ctx)

    # Load or create pool state
    state = load_pool_state(pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            assignments=(),
        )

    # Check if branch is already assigned
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        # Branch already assigned - return existing slot path
        ctx.feedback.info(f"Branch '{branch_name}' already assigned to {existing.slot_name}")
        return existing.worktree_path

    # Find next available slot
    slot_num = find_next_available_slot(state)
    if slot_num is None:
        # Pool is full - handle interactively or with --force
        to_unassign = handle_pool_full_interactive(state, force, sys.stdin.isatty())
        if to_unassign is None:
            raise SystemExit(1) from None

        # Remove the assignment from state
        new_assignments = tuple(
            a for a in state.assignments if a.slot_name != to_unassign.slot_name
        )
        state = PoolState(
            version=state.version,
            pool_size=state.pool_size,
            assignments=new_assignments,
        )
        save_pool_state(pool_json_path, state)
        user_output(
            click.style("✓ ", fg="green")
            + f"Unassigned {click.style(to_unassign.branch_name, fg='yellow')} "
            + f"from {click.style(to_unassign.slot_name, fg='cyan')}"
        )

        # Retry finding a slot - should now succeed
        slot_num = find_next_available_slot(state)
        if slot_num is None:
            user_output("Error: Failed to find available slot after unassigning")
            raise SystemExit(1) from None

    slot_name = generate_slot_name(slot_num)
    worktree_path = worktrees_dir / slot_name

    # Check if branch exists
    local_branches = ctx.git.list_local_branches(repo_root)
    branch_exists = branch_name in local_branches

    if not branch_exists:
        # Create branch from trunk
        trunk = ctx.git.detect_trunk_branch(repo_root)
        ctx.git.create_branch(repo_root, branch_name, trunk)
        ctx.feedback.info(f"Created branch: {branch_name}")

    # Create worktree directory if it doesn't exist
    if not ctx.git.path_exists(worktree_path):
        worktree_path.mkdir(parents=True, exist_ok=True)
        ctx.git.add_worktree(
            repo_root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        # Worktree exists - checkout the branch
        ctx.git.checkout_branch(worktree_path, branch_name)

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
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))

    return worktree_path


def _setup_impl_folder(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    plan_source: PlanSource,
    issue_number: int,
    issue_url: str,
    issue_title: str,
) -> Path:
    """Set up .impl/ folder in the worktree with plan content and issue reference.

    Args:
        ctx: Erk context
        worktree_path: Path to worktree
        plan_source: Plan source with content
        issue_number: GitHub issue number
        issue_url: GitHub issue URL
        issue_title: GitHub issue title

    Returns:
        Path to .impl/ directory
    """
    # Create .impl/ folder with plan content
    # Use overwrite=True since pool slots may have stale .impl/ folders
    ctx.feedback.info("Creating .impl/ folder with plan...")
    impl_path = create_impl_folder(
        worktree_path=worktree_path,
        plan_content=plan_source.plan_content,
        prompt_executor=ctx.prompt_executor,
        overwrite=True,
    )

    # Save issue reference for PR linking
    save_issue_reference(impl_path, issue_number, issue_url, issue_title)
    ctx.feedback.success(f"✓ Created .impl/ folder linked to #{issue_number}")

    return impl_path


@click.command("implement", cls=CommandWithHiddenOptions)
@click.argument("target")
@implement_common_options
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.pass_obj
def pooled_implement(
    ctx: ErkContext,
    target: str,
    force: bool,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    script: bool,
    yolo: bool,
    verbose: bool,
    model: str | None,
) -> None:
    """Assign GitHub issue to a pool slot and execute implementation.

    This command combines pool slot assignment with implementation:

    1. Fetches the GitHub issue and extracts the plan
    2. Assigns the issue's branch to an available pool slot
    3. Sets up .impl/ folder with plan content
    4. Executes Claude for implementation

    TARGET must be a GitHub issue number (e.g., 123 or #123) or URL.
    The issue must have the 'erk-plan' label.

    The key difference from `erk implement` is that this command uses pool
    slots instead of creating new worktrees. This is useful for parallel
    execution of multiple plans without creating many worktrees.

    Examples:

    \b
      # Interactive mode (default)
      erk pooled implement 123

    \b
      # Non-interactive mode
      erk pooled implement 123 --no-interactive

    \b
      # YOLO mode - full automation
      erk pooled implement 123 --yolo

    \b
      # Force unassign if pool is full
      erk pooled implement 123 --force
    """
    # Handle --yolo flag
    if yolo:
        dangerous = True
        submit = True
        no_interactive = True

    # Normalize model name
    model = normalize_model_name(model)

    # Validate flag combinations
    validate_flags(submit, no_interactive, script)

    # Detect target type - must be issue number or URL
    target_info = detect_target_type(target)

    if target_info.target_type == "file_path":
        user_output(
            click.style("Error: ", fg="red")
            + "pooled implement only supports GitHub issues.\n"
            + "Use 'erk implement' for plan files."
        )
        raise SystemExit(1) from None

    if target_info.issue_number is None:
        user_output(click.style("Error: ", fg="red") + "Failed to extract issue number from target")
        raise SystemExit(1) from None

    issue_number = target_info.issue_number

    ctx.feedback.info(f"Detected GitHub issue #{issue_number}")

    # Discover repo context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Get trunk branch (pool slots always start from trunk)
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)

    # Prepare plan source from issue
    issue_plan_source = prepare_plan_source_from_issue(
        ctx, repo.root, issue_number, base_branch=trunk_branch
    )

    # Handle dry-run mode
    if dry_run:
        dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
        user_output(dry_run_header + " No changes will be made\n")

        mode = "non-interactive" if no_interactive else "interactive"
        user_output(f"Execution mode: {mode}\n")

        user_output(f"Would assign branch '{issue_plan_source.branch_name}' to a pool slot")
        user_output(f"  {issue_plan_source.plan_source.dry_run_description}")

        # Show command sequence
        commands = build_command_sequence(submit)
        user_output("\nCommand sequence:")
        for i, cmd in enumerate(commands, 1):
            cmd_args = build_claude_args(cmd, dangerous, model)
            user_output(f"  {i}. {' '.join(cmd_args)}")

        return

    # Assign branch to pool slot
    worktree_path = _assign_branch_to_slot(
        ctx,
        repo_root=repo.root,
        worktrees_dir=repo.worktrees_dir,
        pool_json_path=repo.pool_json_path,
        branch_name=issue_plan_source.branch_name,
        force=force,
    )

    # Fetch issue details for PR linking
    plan = ctx.plan_store.get_plan(repo.root, issue_number)

    # Set up .impl/ folder
    _setup_impl_folder(
        ctx,
        worktree_path=worktree_path,
        plan_source=issue_plan_source.plan_source,
        issue_number=int(issue_number),
        issue_url=plan.url,
        issue_title=plan.title,
    )

    # Execute based on mode
    if script:
        # Script mode - output activation script
        branch = issue_plan_source.branch_name
        target_description = f"#{issue_number}"
        output_activation_instructions(
            ctx,
            wt_path=worktree_path,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            model=model,
            target_description=target_description,
        )
    elif no_interactive:
        # Non-interactive mode - execute via subprocess
        commands = build_command_sequence(submit)
        execute_non_interactive_mode(
            worktree_path=worktree_path,
            commands=commands,
            dangerous=dangerous,
            verbose=verbose,
            model=model,
            executor=ctx.claude_executor,
        )
    else:
        # Interactive mode - hand off to Claude (never returns)
        execute_interactive_mode(
            ctx, repo.root, worktree_path, dangerous, model, ctx.claude_executor
        )
