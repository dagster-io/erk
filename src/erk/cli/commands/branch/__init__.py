"""Branch management commands."""

import click

from erk.cli.alias import alias, register_with_aliases
from erk.cli.commands.branch.checkout_cmd import branch_checkout
from erk.cli.commands.branch.create_cmd import branch_create
from erk.cli.commands.branch.delete_cmd import branch_delete
from erk.cli.commands.branch.list_cmd import branch_list
from erk.cli.help_formatter import ErkCommandGroup


@alias("br")
@click.group("branch", cls=ErkCommandGroup, grouped=False)
def branch_group() -> None:
    """Manage branches."""
    pass


# Register subcommands
branch_group.add_command(branch_create)
branch_group.add_command(branch_delete)
register_with_aliases(branch_group, branch_checkout)
register_with_aliases(branch_group, branch_list)
