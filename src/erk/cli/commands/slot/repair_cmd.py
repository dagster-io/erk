"""Slot repair command - remove stale assignments from pool state."""

import click

from erk.cli.commands.slot.check_cmd import _check_orphan_states
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_confirm, user_output


def find_stale_assignments(
    ctx: ErkContext,
    state: PoolState,
) -> list[SlotAssignment]:
    """Find assignments where the worktree directory doesn't exist.

    Args:
        ctx: Erk context (for git.path_exists)
        state: Pool state to check

    Returns:
        List of stale SlotAssignments
    """
    # Use existing check logic to find orphan states
    issues = _check_orphan_states(state.assignments, ctx)

    # Collect the slot names that have orphan-state issues
    stale_slot_names = {
        issue.message.split(":")[0].replace("Slot ", "")
        for issue in issues
        if issue.code == "orphan-state"
    }

    # Return the actual assignments that are stale
    return [a for a in state.assignments if a.slot_name in stale_slot_names]


def execute_repair(
    state: PoolState,
    stale_assignments: list[SlotAssignment],
) -> PoolState:
    """Create new pool state with stale assignments removed.

    Args:
        state: Current pool state
        stale_assignments: Assignments to remove

    Returns:
        New PoolState with stale assignments filtered out
    """
    stale_slot_names = {a.slot_name for a in stale_assignments}
    new_assignments = tuple(a for a in state.assignments if a.slot_name not in stale_slot_names)

    return PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=state.slots,
        assignments=new_assignments,
    )


@click.command("repair")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def slot_repair(ctx: ErkContext, force: bool) -> None:
    """Remove stale assignments from pool state.

    Finds assignments where the worktree directory no longer exists
    and removes them from pool.json.

    Use --force to skip the confirmation prompt.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk slot create` first.")
        raise SystemExit(1) from None

    # Find stale assignments
    stale_assignments = find_stale_assignments(ctx, state)

    if not stale_assignments:
        user_output(click.style("✓ No stale assignments found", fg="green"))
        return

    # Show what will be repaired
    user_output(f"Found {len(stale_assignments)} stale assignment(s):")
    for assignment in stale_assignments:
        user_output(
            f"  - {click.style(assignment.slot_name, fg='cyan')}: "
            f"branch '{click.style(assignment.branch_name, fg='yellow')}' "
            f"(worktree missing)"
        )

    # Prompt for confirmation unless --force
    if not force:
        if not user_confirm("\nRemove these stale assignments?", default=True):
            user_output("Aborted.")
            return

    # Execute repair
    new_state = execute_repair(state, stale_assignments)
    save_pool_state(repo.pool_json_path, new_state)

    user_output("")
    user_output(
        click.style("✓ ", fg="green") + f"Removed {len(stale_assignments)} stale assignment(s)"
    )
