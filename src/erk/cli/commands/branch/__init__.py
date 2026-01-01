"""Branch management commands."""

import click

from erk.cli.alias import alias, register_with_aliases
from erk.cli.commands.branch.checkout_cmd import branch_checkout
from erk.cli.commands.branch.land_cmd import br_land
from erk.cli.commands.branch.list_cmd import branch_list
from erk.cli.help_formatter import ErkCommandGroup


@alias("br")
@click.group("branch", cls=ErkCommandGroup, grouped=False)
def branch_group() -> None:
    """Manage branches."""
    pass


# Register subcommands
register_with_aliases(branch_group, branch_checkout)
register_with_aliases(branch_group, br_land)
register_with_aliases(branch_group, branch_list)
