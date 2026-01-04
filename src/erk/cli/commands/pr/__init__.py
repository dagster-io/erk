"""PR management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pr.check_cmd import pr_check
from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.fix_conflicts_cmd import pr_fix_conflicts
from erk.cli.commands.pr.submit_cmd import pr_submit
from erk.cli.commands.pr.sync_cmd import pr_sync


@click.group("pr")
def pr_group() -> None:
    """Manage pull requests."""
    pass


pr_group.add_command(pr_check, name="check")
register_with_aliases(pr_group, pr_checkout)
pr_group.add_command(pr_fix_conflicts, name="fix-conflicts")
pr_group.add_command(pr_submit, name="submit")
pr_group.add_command(pr_sync, name="sync")
