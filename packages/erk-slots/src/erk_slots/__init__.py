"""Worktree pool slot management plugin for erk."""

import click

from erk_shared.cli_alias import register_with_aliases
from erk_shared.cli_group import ErkCommandGroup
from erk_slots.assign_cmd import slot_assign
from erk_slots.checkout_cmd import slot_checkout
from erk_slots.init_pool_cmd import slot_init_pool
from erk_slots.list_cmd import slot_list
from erk_slots.repair_cmd import slot_repair
from erk_slots.unassign_cmd import slot_unassign


@click.group("slot", cls=ErkCommandGroup, grouped=False)
def slot_group() -> None:
    """Manage worktree pool slots."""
    pass


slot_group.add_command(slot_assign)
register_with_aliases(slot_group, slot_checkout)
slot_group.add_command(slot_init_pool)
slot_group.add_command(slot_repair)
slot_group.add_command(slot_unassign)
register_with_aliases(slot_group, slot_list)
