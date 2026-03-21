"""Slot goto command - navigate to an existing slot by number or name."""

from contextlib import nullcontext

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.core.script_error import script_error_handler
from erk_shared.output.output import user_output
from erk_shared.slots.naming import generate_slot_name


@click.command("goto", cls=CommandWithHiddenOptions)
@click.argument("slot", metavar="SLOT")
@script_option
@click.pass_obj
def slot_goto(ctx: ErkContext, slot: str, script: bool) -> None:
    """Navigate to an existing slot by number or name.

    SLOT is either a slot number (e.g., 3) or full slot name (e.g., erk-slot-03).

    Navigate to target slot:
      source <(erk slot goto SLOT --script)

    Examples:

        erk slot goto 1              # Navigate to slot 1
        erk slot goto erk-slot-01    # Navigate using full slot name
    """
    with script_error_handler(ctx) if script else nullcontext():
        _slot_goto_body(ctx, slot=slot, script=script)


def _slot_goto_body(ctx: ErkContext, *, slot: str, script: bool) -> None:
    repo = discover_repo_context(ctx, ctx.cwd)

    # Parse slot argument: if numeric, convert to full slot name
    if slot.isdigit():
        slot_name = generate_slot_name(int(slot))
    else:
        slot_name = slot

    # Load pool state
    state = load_pool_state(repo.pool_json_path)

    # Find matching assignment
    assignment = None
    if state is not None:
        for a in state.assignments:
            if a.slot_name == slot_name:
                assignment = a
                break

    if assignment is None:
        user_output(f"Error: Slot {slot_name} is not assigned to any branch")
        raise SystemExit(1) from None

    worktree_path = assignment.worktree_path

    if not worktree_path.exists():
        user_output(f"Error: Worktree path does not exist: {worktree_path}")
        raise SystemExit(1) from None

    msg = (
        click.style("✓ ", fg="green")
        + f"Navigating to {click.style(slot_name, fg='cyan')} "
        + f"({click.style(assignment.branch_name, fg='yellow')})"
    )

    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=assignment.branch_name,
        script=script,
        command_name="slot-goto",
        script_message=f'echo "Navigating to {slot_name} ({assignment.branch_name})"',
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(msg)
        script_path = ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )
        same_worktree = (
            worktree_path.exists()
            and ctx.cwd.exists()
            and worktree_path.resolve() == ctx.cwd.resolve()
        )
        print_activation_instructions(
            script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=same_worktree,
        )
