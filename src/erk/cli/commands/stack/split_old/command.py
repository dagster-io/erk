"""Split command - CLI entry point, validation, and orchestration."""

from pathlib import Path

import click

from erk.cli.commands.stack.split_old.display import (
    confirm_split,
    display_creation_preview,
    display_results,
    display_stack_preview,
)
from erk.cli.commands.stack.split_old.plan import (
    create_split_plan,
    execute_split_plan,
    get_stack_branches,
)
from erk.cli.core import discover_repo_context
from erk.cli.graphite_command import GraphiteCommand
from erk.core.context import ErkContext
from erk_shared.naming import sanitize_worktree_name
from erk_shared.output.output import user_output

# Validation functions


def validate_flags(up: bool, down: bool) -> None:
    """Validate that --up and --down are not used together.

    Raises:
        SystemExit: If both flags are set
    """
    if up and down:
        user_output(click.style("❌ Error: Cannot use --up and --down together", fg="red"))
        user_output(
            "Use either --up (split upstack) or --down (split downstack) or neither (full stack)"
        )
        raise SystemExit(1)


def validate_trunk_branch(trunk_branch: str | None) -> None:
    """Validate trunk branch is available.

    Raises:
        SystemExit: If trunk branch cannot be determined
    """
    if not trunk_branch:
        user_output(click.style("❌ Error: Cannot determine trunk branch", fg="red"))
        user_output("Initialize repository or configure trunk branch")
        raise SystemExit(1)


def check_uncommitted_changes(
    ctx: ErkContext,
    current_worktree: Path,
    force: bool,
    dry_run: bool,
) -> None:
    """Check for uncommitted changes unless --force or --dry-run.

    Raises:
        SystemExit: If uncommitted changes detected
    """
    if not force and not dry_run:
        if ctx.git.has_uncommitted_changes(current_worktree):
            user_output(click.style("❌ Error: Uncommitted changes detected", fg="red", bold=True))
            user_output("\nCommit or stash changes before running split")
            raise SystemExit(1)


# Stack filtering


def apply_stack_filter(
    stack_branches: list[str],
    current_branch: str | None,
    up: bool,
    down: bool,
) -> list[str]:
    """Apply --up or --down filters to determine which branches to split.

    Args:
        stack_branches: Full stack from trunk to leaf
        current_branch: Currently checked out branch (None if detached)
        up: If True, only split upstack (current to leaf)
        down: If True, only split downstack (trunk to current)

    Returns:
        Filtered list of branches to split

    Notes:
        - If both up and down are False, returns full stack
        - If current_branch is None, filters have no effect
        - If current_branch is not in stack, returns empty list
    """
    if up and current_branch is not None:
        # Only split upstack (from current to leaf)
        if current_branch in stack_branches:
            current_index = stack_branches.index(current_branch)
            return stack_branches[current_index:]
        else:
            # Current branch not in stack, split nothing
            return []
    elif down and current_branch is not None:
        # Only split downstack (from trunk to current)
        if current_branch in stack_branches:
            current_index = stack_branches.index(current_branch)
            return stack_branches[: current_index + 1]
        else:
            # Current branch not in stack, split nothing
            return []
    else:
        # Split entire stack
        return stack_branches


# Main CLI command


@click.command("split", cls=GraphiteCommand)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what worktrees would be created without executing",
)
@click.option(
    "--up",
    is_flag=True,
    help="Only split upstack (current branch to leaf). Default is entire stack.",
)
@click.option(
    "--down",
    is_flag=True,
    help="Only split downstack (trunk to current branch). Default is entire stack.",
)
@click.pass_obj
def split_cmd(ctx: ErkContext, *, force: bool, dry_run: bool, up: bool, down: bool) -> None:
    """Split a stack into individual worktrees per branch.

    This is the inverse of consolidate - it creates individual worktrees for each
    branch in the stack (except trunk and the current branch).

    By default, splits the full stack (trunk to leaf). With --up or --down, splits
    only a portion of the stack.

    This command is useful after consolidating branches for operations like
    'gt restack', allowing you to return to the ephemeral worktree pattern.

    \b
    Examples:
      # Split full stack into individual worktrees (default)
      $ erk split

      # Split only upstack (current to leaf)
      $ erk split --up

      # Split only downstack (trunk to current)
      $ erk split --down

      # Preview changes without executing
      $ erk split --dry-run

      # Skip confirmation prompt
      $ erk split --force

    Notes:
    - Trunk branch (main/master) stays in root worktree
    - Current branch cannot get its own worktree (already checked out)
    - Existing worktrees are preserved (idempotent operation)
    - Creates worktrees in the .erks directory
    """
    # 1. Validate input flags
    validate_flags(up, down)

    # 2. Gather repository context
    current_worktree = ctx.cwd
    current_branch = ctx.git.get_current_branch(current_worktree)
    repo = discover_repo_context(ctx, current_worktree)
    trunk_branch = ctx.trunk_branch
    validate_trunk_branch(trunk_branch)
    # After validation, trunk_branch is guaranteed to be non-None
    assert trunk_branch is not None  # Type narrowing for mypy/ty

    # 3. Get stack branches
    stack_branches = get_stack_branches(ctx, repo.root, current_branch, trunk_branch)

    # 4. Apply stack filters
    stack_to_split = apply_stack_filter(stack_branches, current_branch, up, down)

    # 5. Safety checks
    check_uncommitted_changes(ctx, current_worktree, force, dry_run)

    # 6. Create split plan
    all_worktrees = ctx.git.list_worktrees(repo.root)
    plan = create_split_plan(
        stack_branches=stack_to_split,
        trunk_branch=trunk_branch,
        current_branch=current_branch,
        all_worktrees=all_worktrees,
        worktrees_dir=repo.worktrees_dir,
        sanitize_worktree_name=sanitize_worktree_name,
        source_worktree_path=current_worktree,
        repo_root=repo.root,
    )

    # 7. Display preview
    display_stack_preview(stack_to_split, trunk_branch, current_branch, plan)
    display_creation_preview(plan, dry_run)

    # Early exit if nothing to do
    if not plan.branches_to_split:
        return

    # 8. Get user confirmation
    confirm_split(ctx.console, force=force, dry_run=dry_run)

    # 9. Execute or simulate
    user_output("")
    if dry_run:
        results = [(branch, plan.target_paths[branch]) for branch in plan.branches_to_split]
    else:
        results = execute_split_plan(plan, ctx.git)

    # 10. Display results
    display_results(results, dry_run)
