"""Consolidate worktrees by removing others containing branches from current stack."""

import time
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.core.consolidation_utils import calculate_stack_range, create_consolidation_plan
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


def _format_section_header(text: str, separator_length: int = 59) -> str:
    """Format a section header with styled text and separator line."""
    header = click.style(text, bold=True)
    separator = "─" * separator_length
    return f"{header}\n{separator}"


def _format_consolidation_plan(
    stack_branches: list[str],
    current_branch: str,
    consolidated_branches: list[str],
    target_name: str,
    worktrees_to_remove: list[tuple[str, Path]],
) -> str:
    """Format the consolidation plan section with visual hierarchy."""
    lines: list[str] = []

    # Section header
    lines.append(_format_section_header("📋 Consolidation Plan"))
    lines.append("")

    # Branches consolidating to current worktree
    lines.append("Branches consolidating to current worktree:")
    for branch in consolidated_branches:
        if branch == current_branch:
            branch_display = click.style(branch, fg="bright_green", bold=True)
            lines.append(f"  • {branch_display} ← (keeping this worktree)")
        else:
            lines.append(f"  • {branch}")

    lines.append("")

    # Worktrees to remove
    lines.append("Worktrees to remove:")
    for branch, path in worktrees_to_remove:
        lines.append(f"  • {branch}")
        lines.append(f"    {click.style(str(path), fg='white', dim=True)}")

    lines.append("")
    lines.append("─" * 59)

    return "\n".join(lines)


def _format_removal_progress(removed_paths: list[Path]) -> str:
    """Format the removal execution output with grouped checkmarks."""
    lines: list[str] = []

    lines.append(_format_section_header("🗑️  Removing worktrees..."))
    for path in removed_paths:
        lines.append(f"  ✓ {click.style(str(path), fg='green')}")

    return "\n".join(lines)


@click.command("consolidate")
@click.argument("branch", required=False, default=None)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Create and consolidate into a new worktree with this name",
)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without executing",
)
@click.option(
    "--down",
    is_flag=True,
    help="Only consolidate downstack (trunk to current branch). Default is entire stack.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.pass_obj
def consolidate_stack(
    ctx: ErkContext,
    branch: str | None,
    name: str | None,
    force: bool,
    dry_run: bool,
    down: bool,
    script: bool,
) -> None:
    """Consolidate stack branches into a single worktree.

    By default, consolidates full stack (trunk to leaf). With --down, consolidates
    only downstack branches (trunk to current).

    This command removes other worktrees that contain branches from the stack,
    ensuring branches exist in only one worktree. This is useful before
    stack-wide operations like 'gt restack'.

    BRANCH: Optional branch name. If provided, consolidate only from trunk up to
    this branch (partial consolidation). Cannot be used with --down.

    \b
    Examples:
      # Consolidate full stack into current worktree (default)
      $ erk consolidate

      # Consolidate only downstack (trunk to current)
      $ erk consolidate --down

      # Consolidate trunk → feat-2 only (leaves feat-3+ in separate worktrees)
      $ erk consolidate feat-2

      # Create new worktree "my-stack" and consolidate full stack into it
      $ erk consolidate --name my-stack

      # Consolidate downstack into new worktree
      $ erk consolidate --down --name my-partial

      # Preview changes without executing
      $ erk consolidate --dry-run

      # Skip confirmation prompt
      $ erk consolidate --force

    Safety checks:
    - Aborts if any worktree being consolidated has uncommitted changes
    - Preserves the current worktree (or creates new one with --name)
    - Shows preview before removal (unless --force)
    - Never removes root worktree
    """
    # During dry-run, always show output regardless of shell integration
    if dry_run:
        script = False

    # Validate that --down and BRANCH are not used together
    if down and branch is not None:
        user_output(click.style("❌ Error: Cannot use --down with BRANCH argument", fg="red"))
        user_output(
            "Use either --down (consolidate trunk to current) or "
            "BRANCH (consolidate trunk to BRANCH)"
        )
        raise SystemExit(1)

    # Get current worktree and branch
    current_worktree = ctx.cwd
    current_branch = ctx.git.get_current_branch(current_worktree)

    if current_branch is None:
        user_output("Error: Current worktree is in detached HEAD state")
        user_output("Checkout a branch before running consolidate")
        raise SystemExit(1)

    # Get repository root
    repo = discover_repo_context(ctx, current_worktree)
    ensure_erk_metadata_dir(repo)

    # Get current branch's stack
    stack_branches = ctx.graphite.get_branch_stack(ctx.git, repo.root, current_branch)
    if stack_branches is None:
        user_output(f"Error: Branch '{current_branch}' is not tracked by Graphite")
        user_output(
            "Run 'gt repo init' to initialize Graphite, or use 'gt track' to track this branch"
        )
        raise SystemExit(1)

    # Validate branch argument if provided
    if branch is not None:
        if branch not in stack_branches:
            user_output(
                click.style(f"❌ Error: Branch '{branch}' is not in the current stack", fg="red")
            )
            user_output("\nCurrent stack:")
            for b in stack_branches:
                marker = " ← current" if b == current_branch else ""
                user_output(f"  {click.style(b, fg='cyan')}{marker}")
            raise SystemExit(1)

    # Determine which portion of the stack to consolidate (now handled by utility)
    # This will be used in create_consolidation_plan() below

    # Get all worktrees
    all_worktrees = ctx.git.list_worktrees(repo.root)

    # Validate --name argument if provided
    if name is not None:
        # Check if a worktree with this name already exists
        existing_names = [wt.path.name for wt in all_worktrees]

        if name in existing_names:
            user_output(click.style(f"❌ Error: Worktree '{name}' already exists", fg="red"))
            user_output("\nSuggested action:")
            user_output("  1. Use a different name")
            user_output(f"  2. Remove existing worktree: erk remove {name}")
            user_output("  3. Switch to existing: erk checkout <branch>")
            raise SystemExit(1)

    # Calculate stack range early (needed for safety check)
    # If --down is set, force end_branch to be current_branch
    end_branch = current_branch if down else branch
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)

    # Check worktrees in stack for uncommitted changes
    # Only check worktrees that will actually be removed (skip root and current)
    worktrees_with_changes: list[Path] = []
    for wt in all_worktrees:
        if wt.branch not in stack_to_consolidate:
            continue
        # Skip root worktree (never removed)
        if wt.is_root:
            continue
        # Skip current worktree (consolidation target, never removed)
        if wt.path.resolve() == current_worktree.resolve():
            continue
        if ctx.git.path_exists(wt.path) and ctx.git.has_uncommitted_changes(wt.path):
            worktrees_with_changes.append(wt.path)

    if worktrees_with_changes:
        user_output(
            click.style("Error: Uncommitted changes detected in worktrees:", fg="red", bold=True)
        )
        for wt_path in worktrees_with_changes:
            user_output(f"  - {wt_path}")
        user_output("\nCommit or stash changes before running consolidate")
        raise SystemExit(1)

    # Safety check passed - all worktrees are clean
    user_output(
        click.style("✅ Safety check: All worktrees have no uncommitted changes", fg="green")
    )
    user_output()

    # Create new worktree if --name is provided
    # Track temp branch name for cleanup after source worktree removal
    temp_branch_name: str | None = None

    if name is not None:
        if not dry_run:
            # Generate temporary branch name to avoid "already used by worktree" error
            # when the source worktree and new worktree would have the same branch checked out
            temp_branch_name = f"temp-consolidate-{int(time.time())}"

            # Use proper erks directory path resolution
            new_worktree_path = worktree_path_for(repo.worktrees_dir, name)

            # Create temporary branch on current commit (doesn't checkout)
            # Git operations use check=True, so failures raise CalledProcessError
            ctx.git.create_branch(current_worktree, temp_branch_name, current_branch)

            # Checkout temporary branch in source worktree to free up the original branch
            ctx.git.checkout_branch(current_worktree, temp_branch_name)

            # Track temporary branch with Graphite
            ctx.graphite.track_branch(current_worktree, temp_branch_name, current_branch)

            # Create new worktree with original branch
            # (now available since source is on temp branch)
            ctx.git.add_worktree(
                repo.root,
                new_worktree_path,
                branch=current_branch,
                ref=None,
                create_branch=False,
            )

            user_output(click.style(f"✅ Created new worktree: {name}", fg="green"))

            # Change to new worktree directory BEFORE removing source worktree
            # This prevents the shell from being in a deleted directory
            # Always change directory regardless of script mode to ensure we're not in
            # the source worktree when it gets deleted
            if ctx.git.safe_chdir(new_worktree_path):
                # Regenerate context with new cwd (context is immutable)
                ctx = create_context(dry_run=ctx.dry_run)
                user_output(click.style("✅ Changed directory to new worktree", fg="green"))

            target_worktree_path = new_worktree_path
        else:
            user_output(
                click.style(f"[DRY RUN] Would create new worktree: {name}", fg="yellow", bold=True)
            )
            target_worktree_path = current_worktree  # In dry-run, keep current path
    else:
        # Use current worktree as target (existing behavior)
        target_worktree_path = current_worktree

    # Create consolidation plan using utility function
    # Use the same end_branch logic as calculated above
    plan = create_consolidation_plan(
        all_worktrees=all_worktrees,
        stack_branches=stack_branches,
        end_branch=end_branch,
        target_worktree_path=target_worktree_path,
        source_worktree_path=current_worktree if name is not None else None,
    )

    # Extract data from plan for easier reference
    worktrees_to_remove = plan.worktrees_to_remove
    stack_to_consolidate = plan.stack_to_consolidate

    # Display preview
    if not worktrees_to_remove:
        # If using --name, we still need to remove source worktree even if no other worktrees exist
        if name is None:
            user_output("No other worktrees found containing branches from current stack")
            user_output(f"\nCurrent stack branches: {', '.join(stack_branches)}")
            return
        # Continue to source worktree removal when using --name

    # Collect data for formatted output
    worktrees_to_remove_list: list[tuple[str, Path]] = [
        (wt.branch or "detached", wt.path) for wt in worktrees_to_remove
    ]

    # Add source worktree to removal list if creating new worktree
    if name is not None:
        worktrees_to_remove_list.append((current_branch, current_worktree))

    # Display consolidation plan
    user_output()
    plan_output = _format_consolidation_plan(
        stack_branches=stack_branches,
        current_branch=current_branch,
        consolidated_branches=stack_to_consolidate,
        target_name=name if name is not None else str(current_worktree.name),
        worktrees_to_remove=worktrees_to_remove_list,
    )
    user_output(plan_output)

    # Exit if dry-run
    if dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        return

    # Get confirmation unless --force or --script
    if not force and not script:
        user_output()
        if not click.confirm(
            click.style("All worktrees are clean. Proceed with removal?", fg="yellow", bold=True),
            default=False,
        ):
            user_output(click.style("⭕ Aborted", fg="red", bold=True))
            return

    # Shell integration: generate script to activate new worktree BEFORE destructive operations
    # This ensures the shell can navigate even if later steps fail (e.g., branch deletion).
    # The handler will use this script instead of passthrough when available.
    if name is not None and script and not dry_run:
        script_content = render_activation_script(
            worktree_path=target_worktree_path,
            final_message='echo "✓ Went to consolidated worktree."',
            comment="work activate-script (consolidate)",
        )
        activation_result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="consolidate",
            comment=f"activate {name}",
        )
        activation_result.output_for_shell_integration()

    # Remove worktrees and collect paths for progress output
    removed_paths: list[Path] = []

    for wt in worktrees_to_remove:
        ctx.git.remove_worktree(repo.root, wt.path, force=True)
        removed_paths.append(wt.path)

    # Remove source worktree if a new worktree was created
    if name is not None:
        ctx.git.remove_worktree(repo.root, current_worktree.resolve(), force=True)
        removed_paths.append(current_worktree)

        # Delete temporary branch after source worktree is removed
        # (can't delete while it's checked out in the source worktree)
        if temp_branch_name is not None:
            ctx.git.delete_branch(repo.root, temp_branch_name, force=True)

    # Display grouped removal progress
    user_output()
    user_output(_format_removal_progress(removed_paths))

    # Prune stale worktree metadata after all removals
    # (explicit call now that remove_worktree no longer auto-prunes)
    ctx.git.prune_worktrees(repo.root)

    user_output(f"\n{click.style('✅ Consolidation complete', fg='green', bold=True)}")
    user_output()
    user_output("Next step:")
    user_output("  Run 'gt restack' to update branch relationships")

    # Early return when no worktree switch (consolidating into current worktree)
    # Makes it explicit that no script is needed in this case
    if name is None:
        return  # No script needed when not switching worktrees

    # Manual cd instruction when not in script mode
    # (Script mode already output activation script earlier, before destructive operations)
    if not script and not dry_run:
        user_output(f"Going to worktree: {click.style(name, fg='cyan', bold=True)}")
        user_output(f"\n{click.style('ℹ️', fg='blue')} Run this command to switch:")
        user_output(f"  cd {target_worktree_path}")
