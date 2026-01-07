"""Command to implement features from GitHub issues or plan files.

This unified command provides two modes:
- GitHub issue mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md

Both modes assign a pool slot and invoke Claude for implementation.
Can be run from any location, including from within pool slots.
"""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.completions import complete_plan_files
from erk.cli.commands.implement_shared import (
    PlanSource,
    WorktreeCreationResult,
    build_claude_args,
    build_command_sequence,
    detect_target_type,
    determine_base_branch,
    execute_interactive_mode,
    execute_non_interactive_mode,
    implement_common_options,
    normalize_model_name,
    output_activation_instructions,
    prepare_plan_source_from_file,
    prepare_plan_source_from_issue,
    validate_flags,
)
from erk.cli.commands.slot.common import (
    find_branch_assignment,
    find_inactive_slot,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
)
from erk.cli.commands.wt.create_cmd import run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions
from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
    update_slot_objective,
)
from erk_shared.github.metadata.plan_header import extract_plan_header_objective_issue
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.naming import sanitize_worktree_name
from erk_shared.output.output import user_output


def _check_worktree_clean_for_checkout(
    ctx: ErkContext,
    wt_path: Path,
    slot_name: str,
) -> None:
    """Raise ClickException if worktree has uncommitted changes.

    Checks for uncommitted changes before checkout to provide a friendly error
    message with actionable remediation steps, rather than letting git fail
    with an ugly traceback.
    """
    if ctx.git.has_uncommitted_changes(wt_path):
        raise click.ClickException(
            f"Slot '{slot_name}' has uncommitted changes that would be overwritten.\n\n"
            f"Remediation options:\n"
            f"  1. cd {wt_path} && git stash\n"
            f"  2. cd {wt_path} && git commit -am 'WIP'\n"
            f"  3. erk slot unassign {slot_name}  # discard changes and reset slot"
        )


def _create_worktree_with_plan_content(
    ctx: ErkContext,
    *,
    plan_source: PlanSource,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    linked_branch_name: str | None,
    base_branch: str,
    model: str | None,
    force: bool,
    objective_issue: int | None,
) -> WorktreeCreationResult | None:
    """Create worktree with plan content using slot assignment.

    Always assigns a new pool slot for the implementation, even when running
    from within a managed slot. This maximizes parallelism by keeping the
    parent branch assigned to its current slot.

    Args:
        ctx: Erk context
        plan_source: Plan source with content and metadata
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        no_interactive: Whether to execute non-interactively
        linked_branch_name: Optional branch name for issue-based worktrees
                           (when provided, use this branch instead of creating new)
        base_branch: Base branch to use as ref for worktree creation
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        force: Whether to auto-unassign oldest slot if pool is full
        objective_issue: Optional objective issue number from plan metadata

    Returns:
        WorktreeCreationResult with paths, or None if dry-run mode
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Determine branch name
    if linked_branch_name is not None:
        # For issue mode: use the branch created for this issue
        branch = linked_branch_name
    else:
        # For file mode: derive branch from plan name
        branch = sanitize_worktree_name(plan_source.base_name)

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
        ctx.feedback.info(f"Branch '{branch}' already assigned to {slot_name}")

        # Handle dry-run mode
        if dry_run:
            _show_dry_run_output(
                slot_name=slot_name,
                plan_source=plan_source,
                submit=submit,
                dangerous=dangerous,
                no_interactive=no_interactive,
                model=model,
            )
            return None

        # Just update .impl/ folder with new plan content
        ctx.feedback.info("Updating .impl/ folder with plan...")
        create_impl_folder(
            worktree_path=wt_path,
            plan_content=plan_source.plan_content,
            overwrite=True,
        )
        ctx.feedback.success("✓ Updated .impl/ folder")

        return WorktreeCreationResult(
            worktree_path=wt_path,
            impl_dir=wt_path / ".impl",
        )

    # Check if branch already exists locally
    local_branches = ctx.git.list_local_branches(repo_root)
    use_existing_branch = branch in local_branches

    # Find available slot
    inactive_slot = find_inactive_slot(state, ctx.git, repo_root)
    if inactive_slot is not None:
        # Fast path: reuse existing worktree
        slot_name, wt_path = inactive_slot
    else:
        # Find next available slot number
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

            # Use the slot we just unassigned (it has a worktree directory that can be reused)
            slot_name = to_unassign.slot_name
            wt_path = to_unassign.worktree_path
        else:
            slot_name = generate_slot_name(slot_num)
            wt_path = repo.worktrees_dir / slot_name

    # Handle dry-run mode
    if dry_run:
        _show_dry_run_output(
            slot_name=slot_name,
            plan_source=plan_source,
            submit=submit,
            dangerous=dangerous,
            no_interactive=no_interactive,
            model=model,
        )
        return None

    # Create worktree at slot path
    ctx.feedback.info(f"Assigning to slot '{slot_name}'...")

    # Load local config
    config = ctx.local_config if ctx.local_config is not None else LoadedConfig.test()

    # Respect global use_graphite config
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    if inactive_slot is not None:
        # Fast path: checkout branch in existing worktree
        # Check for uncommitted changes before checkout
        _check_worktree_clean_for_checkout(ctx, wt_path, slot_name)
        if use_existing_branch:
            ctx.feedback.info(f"Checking out existing branch '{branch}'...")
            ctx.git.checkout_branch(wt_path, branch)
        else:
            # Create branch and checkout
            ctx.feedback.info(f"Creating branch '{branch}' from {base_branch}...")
            ctx.git.create_branch(repo_root, branch, base_branch)
            if use_graphite:
                ctx.graphite.track_branch(repo_root, branch, base_branch)
            ctx.git.checkout_branch(wt_path, branch)
    else:
        # On-demand slot creation
        if not use_existing_branch:
            # Create branch first
            ctx.feedback.info(f"Creating branch '{branch}' from {base_branch}...")
            ctx.git.create_branch(repo_root, branch, base_branch)
            if use_graphite:
                ctx.graphite.track_branch(repo_root, branch, base_branch)

        # Check if worktree directory already exists (from pool initialization)
        if wt_path.exists():
            # Check for uncommitted changes before checkout
            _check_worktree_clean_for_checkout(ctx, wt_path, slot_name)
            # Worktree already exists - check out the branch
            ctx.git.checkout_branch(wt_path, branch)
        else:
            # Create directory for worktree
            wt_path.mkdir(parents=True, exist_ok=True)

            # Add worktree
            ctx.git.add_worktree(
                repo_root,
                wt_path,
                branch=branch,
                ref=None,
                create_branch=False,
            )

    ctx.feedback.success(f"✓ Assigned {branch} to {slot_name}")

    # Create slot assignment
    now = ctx.time.now().isoformat()
    new_assignment = SlotAssignment(
        slot_name=slot_name,
        branch_name=branch,
        assigned_at=now,
        worktree_path=wt_path,
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

    # Update slot with objective (if provided)
    if objective_issue is not None:
        # Check if slot exists in slots list
        slot_exists = any(s.name == slot_name for s in new_state.slots)
        if slot_exists:
            # Update existing slot
            new_state = update_slot_objective(new_state, slot_name, objective_issue)
        else:
            # Add new slot with objective
            new_slot = SlotInfo(name=slot_name, last_objective_issue=objective_issue)
            new_state = PoolState(
                version=new_state.version,
                pool_size=new_state.pool_size,
                slots=(*new_state.slots, new_slot),
                assignments=new_state.assignments,
            )
        save_pool_state(repo.pool_json_path, new_state)
        ctx.feedback.info(f"Linked to objective #{objective_issue}")

    # Run post-worktree setup
    run_post_worktree_setup(
        ctx, config=config, worktree_path=wt_path, repo_root=repo_root, name=slot_name
    )

    # Create .impl/ folder with plan content at worktree root
    ctx.feedback.info("Creating .impl/ folder with plan...")
    create_impl_folder(
        worktree_path=wt_path,
        plan_content=plan_source.plan_content,
        overwrite=True,
    )
    ctx.feedback.success("✓ Created .impl/ folder")

    return WorktreeCreationResult(
        worktree_path=wt_path,
        impl_dir=wt_path / ".impl",
    )


def _show_dry_run_output(
    *,
    slot_name: str,
    plan_source: PlanSource,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    model: str | None,
) -> None:
    """Show dry-run output for slot assignment."""
    dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
    user_output(dry_run_header + " No changes will be made\n")

    # Show execution mode
    mode = "non-interactive" if no_interactive else "interactive"
    user_output(f"Execution mode: {mode}\n")

    user_output(f"Would assign to slot '{slot_name}'")
    user_output(f"  {plan_source.dry_run_description}")

    # Show command sequence
    commands = build_command_sequence(submit)
    user_output("\nCommand sequence:")
    for i, cmd in enumerate(commands, 1):
        cmd_args = build_claude_args(cmd, dangerous, model)
        user_output(f"  {i}. {' '.join(cmd_args)}")


def _implement_from_issue(
    ctx: ErkContext,
    *,
    issue_number: str,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    force: bool,
    executor: ClaudeExecutor,
) -> None:
    """Implement feature from GitHub issue.

    Args:
        ctx: Erk context
        issue_number: GitHub issue number
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        force: Whether to auto-unassign oldest slot if pool is full
        executor: Claude CLI executor for command execution
    """
    # Discover repo context for issue fetch
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Determine base branch (respects worktree stacking)
    base_branch = determine_base_branch(ctx, repo.root)

    # Prepare plan source from issue (creates branch via git)
    issue_plan_source = prepare_plan_source_from_issue(
        ctx, repo.root, issue_number, base_branch=base_branch
    )

    # Extract objective from plan metadata (if present)
    plan = ctx.plan_store.get_plan(repo.root, issue_number)
    objective_issue = extract_plan_header_objective_issue(plan.body)

    # Create worktree with plan content, using the branch name
    result = _create_worktree_with_plan_content(
        ctx,
        plan_source=issue_plan_source.plan_source,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
        linked_branch_name=issue_plan_source.branch_name,
        base_branch=base_branch,
        model=model,
        force=force,
        objective_issue=objective_issue,
    )

    # Early return for dry-run mode
    if result is None:
        return

    wt_path = result.worktree_path

    # Save issue reference for PR linking (issue-specific)
    # Use impl_dir from result to handle monorepo project-root placement
    ctx.feedback.info("Saving issue reference for PR linking...")
    plan = ctx.plan_store.get_plan(repo.root, issue_number)
    save_issue_reference(result.impl_dir, int(issue_number), plan.url, plan.title)

    ctx.feedback.success(f"✓ Saved issue reference: {plan.url}")

    # Execute based on mode
    if script:
        # Script mode - output activation script
        branch = wt_path.name
        target_description = f"#{issue_number}"
        output_activation_instructions(
            ctx,
            wt_path=wt_path,
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
            worktree_path=wt_path,
            commands=commands,
            dangerous=dangerous,
            verbose=verbose,
            model=model,
            executor=executor,
        )
    else:
        # Interactive mode - hand off to Claude (never returns)
        execute_interactive_mode(
            ctx,
            repo_root=repo.root,
            worktree_path=wt_path,
            dangerous=dangerous,
            model=model,
            executor=executor,
        )


def _implement_from_file(
    ctx: ErkContext,
    *,
    plan_file: Path,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    force: bool,
    executor: ClaudeExecutor,
) -> None:
    """Implement feature from plan file.

    Args:
        ctx: Erk context
        plan_file: Path to plan file
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        force: Whether to auto-unassign oldest slot if pool is full
        executor: Claude CLI executor for command execution
    """
    # Discover repo context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Determine base branch (respects worktree stacking)
    base_branch = determine_base_branch(ctx, repo.root)

    # Prepare plan source from file
    plan_source = prepare_plan_source_from_file(ctx, plan_file)

    # Create worktree with plan content
    # File mode has no objective metadata
    result = _create_worktree_with_plan_content(
        ctx,
        plan_source=plan_source,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
        linked_branch_name=None,
        base_branch=base_branch,
        model=model,
        force=force,
        objective_issue=None,
    )

    # Early return for dry-run mode
    if result is None:
        return

    wt_path = result.worktree_path

    # Delete original plan file (move semantics, file-specific)
    ctx.feedback.info(f"Removing original plan file: {plan_file.name}...")
    plan_file.unlink()

    ctx.feedback.success("✓ Moved plan file to worktree")

    # Execute based on mode
    if script:
        # Script mode - output activation script
        branch = wt_path.name
        target_description = str(plan_file)
        output_activation_instructions(
            ctx,
            wt_path=wt_path,
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
            worktree_path=wt_path,
            commands=commands,
            dangerous=dangerous,
            verbose=verbose,
            model=model,
            executor=executor,
        )
    else:
        # Interactive mode - hand off to Claude (never returns)
        execute_interactive_mode(
            ctx,
            repo_root=repo.root,
            worktree_path=wt_path,
            dangerous=dangerous,
            model=model,
            executor=executor,
        )


@alias("impl")
@click.command("implement", cls=CommandWithHiddenOptions)
@click.argument("target", shell_complete=complete_plan_files)
@implement_common_options
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Auto-unassign oldest slot if pool is full (no interactive prompt).",
)
@click.pass_obj
def implement(
    ctx: ErkContext,
    *,
    target: str,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    script: bool,
    yolo: bool,
    verbose: bool,
    force: bool,
    model: str | None,
) -> None:
    """Create worktree from GitHub issue or plan file and execute implementation.

    By default, runs in interactive mode where you can interact with Claude
    during implementation. Use --no-interactive for automated execution.

    TARGET can be:
    - GitHub issue number (e.g., #123 or 123)
    - GitHub issue URL (e.g., https://github.com/user/repo/issues/123)
    - Path to plan file (e.g., ./my-feature-plan.md)

    Note: Plain numbers (e.g., 809) are always interpreted as GitHub issues.
          For files with numeric names, use ./ prefix (e.g., ./809).

    For GitHub issues, the issue must have the 'erk-plan' label.

    Examples:

    \b
      # Interactive mode (default)
      erk implement 123

    \b
      # Interactive mode, skip permissions
      erk implement 123 --dangerous

    \b
      # Non-interactive mode (automated execution)
      erk implement 123 --no-interactive

    \b
      # Full CI/PR workflow (requires --no-interactive)
      erk implement 123 --no-interactive --submit

    \b
      # YOLO mode - full automation (dangerous + submit + no-interactive)
      erk implement 123 --yolo

    \b
      # Shell integration
      source <(erk implement 123 --script)

    \b
      # From plan file
      erk implement ./my-feature-plan.md
    """
    # Handle --yolo flag (shorthand for dangerous + submit + no-interactive)
    if yolo:
        dangerous = True
        submit = True
        no_interactive = True

    # Normalize model name (validates and expands aliases)
    model = normalize_model_name(model)

    # Validate flag combinations
    validate_flags(submit, no_interactive, script)

    # Detect target type
    target_info = detect_target_type(target)

    # Output target detection diagnostic
    if target_info.target_type in ("issue_number", "issue_url"):
        ctx.feedback.info(f"Detected GitHub issue #{target_info.issue_number}")
    elif target_info.target_type == "file_path":
        ctx.feedback.info(f"Detected plan file: {target}")

    if target_info.target_type in ("issue_number", "issue_url"):
        # GitHub issue mode
        if target_info.issue_number is None:
            user_output(
                click.style("Error: ", fg="red") + "Failed to extract issue number from target"
            )
            raise SystemExit(1) from None

        _implement_from_issue(
            ctx,
            issue_number=target_info.issue_number,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            force=force,
            executor=ctx.claude_executor,
        )
    else:
        # Plan file mode
        plan_file = Path(target)
        _implement_from_file(
            ctx,
            plan_file=plan_file,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            force=force,
            executor=ctx.claude_executor,
        )
