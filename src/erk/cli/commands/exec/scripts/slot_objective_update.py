"""Update the slot's objective issue in pool.json.

This exec command updates the last_objective_issue for the current slot,
allowing /erk:objective-next-plan to default to the same objective.

Usage:
    erk exec slot-objective-update --objective-issue=123
    erk exec slot-objective-update --objective-issue=123 --slot-name=erk-slot-01

Output:
    JSON with success status and slot info

Exit Codes:
    0: Success (even if not in a slot)

Examples:
    $ erk exec slot-objective-update --objective-issue=123
    {"success": true, "slot_name": "erk-slot-01", "objective_issue": 123}

    $ erk exec slot-objective-update --objective-issue=123  # Not in a slot
    {"success": true, "slot_name": null, "objective_issue": null, ...}
"""

import json
from pathlib import Path

import click

from erk.core.worktree_pool import (
    load_pool_state,
    save_pool_state,
    update_slot_objective,
)
from erk_shared.context.helpers import require_cwd
from erk_shared.context.types import NoRepoSentinel


def _not_in_slot_result() -> None:
    """Output result when not in a slot worktree."""
    click.echo(
        json.dumps(
            {
                "success": True,
                "slot_name": None,
                "objective_issue": None,
                "message": "Not in a slot worktree",
            }
        )
    )


def _is_path_within(child: Path, parent: Path) -> bool:
    """Check if child path is within parent path."""
    if not parent.exists():
        return False
    parent_resolved = parent.resolve()
    return child == parent_resolved or parent_resolved in child.parents


@click.command(name="slot-objective-update")
@click.option(
    "--objective-issue",
    type=int,
    required=True,
    help="Issue number to set as the slot's last objective",
)
@click.option(
    "--slot-name",
    type=str,
    help="Slot name to update (defaults to current slot based on cwd)",
)
@click.pass_context
def slot_objective_update(
    ctx: click.Context,
    *,
    objective_issue: int,
    slot_name: str | None,
) -> None:
    """Update the slot's last_objective_issue in pool.json.

    Updates the objective for a slot so that future /erk:objective-next-plan
    calls default to this objective.

    If not in a slot worktree and no --slot-name is provided, returns success
    with null values (no-op).
    """
    if ctx.obj is None:
        _not_in_slot_result()
        return

    cwd = require_cwd(ctx)
    repo = ctx.obj.repo

    # Check if we're in a repo
    if isinstance(repo, NoRepoSentinel):
        _not_in_slot_result()
        return

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        _not_in_slot_result()
        return

    # Detect slot name if not provided
    if slot_name is None:
        cwd_resolved = cwd.resolve()

        # First try exact match
        for assignment in state.assignments:
            if not assignment.worktree_path.exists():
                continue
            if assignment.worktree_path.resolve() == cwd_resolved:
                slot_name = assignment.slot_name
                break

        # Fall back to checking if cwd is within an assignment's worktree
        if slot_name is None:
            for assignment in state.assignments:
                if _is_path_within(cwd_resolved, assignment.worktree_path):
                    slot_name = assignment.slot_name
                    break

    if slot_name is None:
        _not_in_slot_result()
        return

    # Update the slot's objective
    new_state = update_slot_objective(state, slot_name, objective_issue)

    # Save the updated state
    save_pool_state(repo.pool_json_path, new_state)

    result = {
        "success": True,
        "slot_name": slot_name,
        "objective_issue": objective_issue,
    }
    click.echo(json.dumps(result))
