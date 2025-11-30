"""PR management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.land_cmd import pr_land
from erk.cli.commands.pr.submit_cmd import pr_submit
from erk.cli.help_formatter import GroupedCommandGroup


@click.group("pr", cls=GroupedCommandGroup)
def pr_group() -> None:
    """Manage pull requests."""
    pass


register_with_aliases(pr_group, pr_checkout)
pr_group.add_command(pr_land, name="land")
pr_group.add_command(pr_submit, name="submit")
