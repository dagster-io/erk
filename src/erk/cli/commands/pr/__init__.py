"""PR management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.pr.address_cmd import address
from erk.cli.commands.pr.check_cmd import pr_check
from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.close_cmd import pr_close
from erk.cli.commands.pr.create_cmd import pr_create
from erk.cli.commands.pr.dispatch.cli import pr_dispatch
from erk.cli.commands.pr.diverge_fix_cmd import pr_diverge_fix
from erk.cli.commands.pr.duplicate_check_cmd import duplicate_check_plan
from erk.cli.commands.pr.list.cli import pr_list
from erk.cli.commands.pr.log_cmd import pr_log
from erk.cli.commands.pr.prepare_cmd import pr_prepare
from erk.cli.commands.pr.rebase_cmd import rebase
from erk.cli.commands.pr.replan_cmd import pr_replan
from erk.cli.commands.pr.rewrite_cmd import pr_rewrite
from erk.cli.commands.pr.submit_cmd import pr_submit
from erk.cli.commands.pr.teleport_cmd import pr_teleport
from erk.cli.commands.pr.view.cli import pr_view


@click.group("pr")
def pr_group() -> None:
    """Manage pull requests."""
    pass


pr_group.add_command(address, name="address")
pr_group.add_command(pr_check, name="check")
register_with_aliases(pr_group, pr_checkout)
pr_group.add_command(pr_close, name="close")
pr_group.add_command(pr_create, name="create")
pr_group.add_command(pr_dispatch, name="dispatch")
pr_group.add_command(duplicate_check_plan, name="duplicate-check")
pr_group.add_command(rebase, name="rebase")
pr_group.add_command(pr_list, name="list")
pr_group.add_command(pr_log, name="log")
pr_group.add_command(pr_prepare, name="prepare")
pr_group.add_command(pr_replan, name="replan")
pr_group.add_command(pr_rewrite, name="rewrite")
pr_group.add_command(pr_submit, name="submit")
pr_group.add_command(pr_teleport, name="teleport")
pr_group.add_command(pr_diverge_fix, name="diverge-fix")
pr_group.add_command(pr_view, name="view")
