"""Branch management commands."""

import click

from erk.cli.alias import alias, register_with_aliases
from erk.cli.commands.branch.checkout_cmd import branch_checkout
from erk.cli.help_formatter import ErkCommandGroup


@alias("br")
@click.group("branch", cls=ErkCommandGroup, grouped=False)
def branch_group() -> None:
    """Manage branches."""
    pass


register_with_aliases(branch_group, branch_checkout)
