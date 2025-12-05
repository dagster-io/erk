"""PR management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pr.auto_restack_cmd import pr_auto_restack
from erk.cli.commands.pr.check_cmd import pr_check
from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.land_cmd import pr_land
from erk.cli.commands.pr.prepare_local_cmd import pr_prepare_local
from erk.cli.commands.pr.submit_cmd import pr_submit
from erk.cli.commands.pr.sync_cmd import pr_sync


@click.group("pr")
def pr_group() -> None:
    """Manage pull requests."""
    pass


pr_group.add_command(pr_auto_restack, name="auto-restack")
pr_group.add_command(pr_check, name="check")
register_with_aliases(pr_group, pr_checkout)
pr_group.add_command(pr_land, name="land")
pr_group.add_command(pr_prepare_local, name="prepare-local")
pr_group.add_command(pr_submit, name="submit")
pr_group.add_command(pr_sync, name="sync")
