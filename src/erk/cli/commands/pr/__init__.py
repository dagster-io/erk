"""PR management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pr.address_cmd import address_group
from erk.cli.commands.pr.check_cmd import pr_check
from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.fix_conflicts_cmd import fix_conflicts_group
from erk.cli.commands.pr.submit_cmd import pr_submit
from erk.cli.commands.pr.summarize_cmd import pr_summarize
from erk.cli.commands.pr.sync_cmd import pr_sync
from erk.cli.commands.pr.sync_divergence_cmd import pr_sync_divergence


@click.group("pr")
def pr_group() -> None:
    """Manage pull requests."""
    pass


pr_group.add_command(address_group, name="address")
pr_group.add_command(pr_check, name="check")
register_with_aliases(pr_group, pr_checkout)
pr_group.add_command(fix_conflicts_group, name="fix-conflicts")
pr_group.add_command(pr_submit, name="submit")
pr_group.add_command(pr_summarize, name="summarize")
pr_group.add_command(pr_sync, name="sync")
pr_group.add_command(pr_sync_divergence, name="sync-divergence")
