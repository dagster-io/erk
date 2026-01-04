"""Get the last objective issue for the current slot.

This exec command looks up the current worktree's slot and returns
the last_objective_issue from pool.json.

Usage:
    erk exec slot-objective

Output:
    JSON with objective_issue (null if not found or not in a slot)

Exit Codes:
    0: Success (even if no objective found)

Examples:
    $ erk exec slot-objective
    {"objective_issue": 123, "slot_name": "erk-managed-wt-01"}

    $ erk exec slot-objective  # Not in a slot worktree
    {"objective_issue": null, "slot_name": null}
"""

import json
from pathlib import Path

import click

from erk.core.worktree_pool import load_pool_state
from erk_shared.context.helpers import require_cwd
from erk_shared.context.types import NoRepoSentinel


def _null_result() -> None:
    """Output null result and return."""
    click.echo(json.dumps({"objective_issue": None, "slot_name": None}))


@click.command(name="slot-objective")
@click.pass_context
def slot_objective(ctx: click.Context) -> None:
    """Get the last objective issue for the current slot.

    Looks up the current worktree in pool.json and returns
    the slot's last_objective_issue if set.
    """
    if ctx.obj is None:
        _null_result()
        return

    cwd = require_cwd(ctx)
    repo = ctx.obj.repo

    # Check if we're in a repo
    if isinstance(repo, NoRepoSentinel):
        _null_result()
        return

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        _null_result()
        return

    # Find assignment for current worktree
    cwd_resolved = cwd.resolve()
    slot_name: str | None = None

    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        if assignment.worktree_path.resolve() == cwd_resolved:
            slot_name = assignment.slot_name
            break

    if slot_name is None:
        # Check if cwd is within an assignment's worktree
        for assignment in state.assignments:
            if _is_path_within(cwd_resolved, assignment.worktree_path):
                slot_name = assignment.slot_name
                break

    if slot_name is None:
        _null_result()
        return

    # Find slot info to get last_objective_issue
    objective_issue: int | None = None
    for slot in state.slots:
        if slot.name == slot_name:
            objective_issue = slot.last_objective_issue
            break

    result = {"objective_issue": objective_issue, "slot_name": slot_name}
    click.echo(json.dumps(result))


def _is_path_within(child: Path, parent: Path) -> bool:
    """Check if child path is within parent path."""
    if not parent.exists():
        return False
    parent_resolved = parent.resolve()
    return child == parent_resolved or parent_resolved in child.parents
