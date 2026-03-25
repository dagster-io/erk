"""Branch management commands."""

import click

from erk.cli.commands.branch.checkout_cmd import branch_checkout
from erk.cli.commands.branch.delete_cmd import branch_delete
from erk.cli.commands.branch.list_cmd import branch_list
from erk_shared.cli_alias import alias, register_with_aliases
from erk_shared.cli_group import ErkCommandGroup


@alias("br")
@click.group("branch", cls=ErkCommandGroup, grouped=False)
def branch_group() -> None:
    """Manage branches."""
    pass


# Register subcommands
register_with_aliases(branch_group, branch_checkout)
branch_group.add_command(branch_delete)
register_with_aliases(branch_group, branch_list)
