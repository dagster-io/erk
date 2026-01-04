"""Slot infrastructure management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.slot.check_cmd import slot_check
from erk.cli.commands.slot.init_pool_cmd import slot_init_pool
from erk.cli.commands.slot.list_cmd import slot_list
from erk.cli.commands.slot.repair_cmd import slot_repair
from erk.cli.help_formatter import ErkCommandGroup


@click.group("slot", cls=ErkCommandGroup, grouped=False)
def slot_group() -> None:
    """Manage worktree pool slots (infrastructure only)."""
    pass


# Register subcommands
slot_group.add_command(slot_check)
slot_group.add_command(slot_init_pool)
slot_group.add_command(slot_repair)
register_with_aliases(slot_group, slot_list)
