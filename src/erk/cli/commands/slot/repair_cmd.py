"""Slot repair command - remove stale assignments from pool state."""

from pathlib import Path

import click

from erk.cli.commands.slot.check_cmd import SyncIssue, run_sync_diagnostics
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment
from erk_shared.output.output import user_confirm, user_output

# Issue codes that can be auto-repaired by removing the assignment
AUTO_REPAIRABLE_CODES = frozenset({"orphan-state"})


def _extract_slot_name(issue: SyncIssue) -> str:
    """Extract slot name from issue message.

    Issue messages have format: "Slot <slot-name>: <description>"
    """
    return issue.message.split(":")[0].replace("Slot ", "")


def _format_remediation(issue: SyncIssue, worktrees_dir: Path) -> list[str]:
    """Format remediation suggestions for an issue.

    Args:
        issue: The sync issue
        worktrees_dir: Path to worktrees directory (for path display)

    Returns:
        List of remediation command strings
    """
    slot_name = _extract_slot_name(issue)
    worktree_path = worktrees_dir / slot_name

    if issue.code == "branch-mismatch":
        # Extract expected branch from message: "pool says 'X', git says 'Y'"
        # Message format: "Slot <slot>: pool says '<expected>', git says '<actual>'"
        parts = issue.message.split("pool says '")
        expected_branch = parts[1].split("'")[0] if len(parts) > 1 else "<expected-branch>"
        return [
            f"erk slot unassign {slot_name}",
            f"cd {worktree_path} && git checkout {expected_branch}",
        ]
    elif issue.code == "missing-branch":
        return [f"erk slot unassign {slot_name}"]
    elif issue.code == "git-registry-missing":
        return [f"erk slot unassign {slot_name}"]
    else:
        return []


def find_stale_assignments(
    state: PoolState,
    issues: list[SyncIssue],
) -> list[SlotAssignment]:
    """Find assignments that can be auto-repaired.

    Args:
        state: Pool state to check
        issues: List of sync issues from run_sync_diagnostics

    Returns:
        List of stale SlotAssignments (orphan-state issues)
    """
    # Collect the slot names that have auto-repairable issues
    stale_slot_names = {
        _extract_slot_name(issue) for issue in issues if issue.code in AUTO_REPAIRABLE_CODES
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


def _display_informational_issues(
    issues: list[SyncIssue],
    worktrees_dir: Path,
) -> None:
    """Display informational issues that require manual intervention.

    Args:
        issues: List of non-auto-repairable issues
        worktrees_dir: Path to worktrees directory (for path display)
    """
    informational = [i for i in issues if i.code not in AUTO_REPAIRABLE_CODES]
    if not informational:
        return

    user_output("")
    user_output(f"Found {len(informational)} issue(s) requiring manual intervention:")
    for issue in informational:
        user_output(f"  [{click.style(issue.code, fg='yellow')}] {issue.message}")
        remediation = _format_remediation(issue, worktrees_dir)
        if remediation:
            user_output("    Remediation:")
            for cmd in remediation:
                user_output(f"      {click.style(cmd, fg='cyan')}")


@click.command("repair")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def slot_repair(ctx: ErkContext, force: bool) -> None:
    """Remove stale assignments from pool state.

    Finds assignments where the worktree directory no longer exists
    and removes them from pool.json.

    Also displays other issues (like branch-mismatch) that require
    manual intervention with suggested remediation commands.

    Use --force to skip the confirmation prompt.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = ctx.repo_state_store.load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk slot create` first.")
        raise SystemExit(1) from None

    # Run full diagnostics to get all issues
    all_issues = run_sync_diagnostics(ctx, state, repo.root)

    # Find stale (auto-repairable) assignments
    stale_assignments = find_stale_assignments(state, all_issues)

    # Display informational issues (non-auto-repairable)
    _display_informational_issues(all_issues, repo.worktrees_dir)

    if not stale_assignments:
        if not any(i.code not in AUTO_REPAIRABLE_CODES for i in all_issues):
            user_output(click.style("✓ No issues found", fg="green"))
        return

    # Show what will be repaired
    user_output("")
    user_output(f"Found {len(stale_assignments)} repairable issue(s):")
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
    ctx.repo_state_store.save_pool_state(repo.pool_json_path, new_state)

    user_output("")
    user_output(
        click.style("✓ ", fg="green") + f"Removed {len(stale_assignments)} stale assignment(s)"
    )
