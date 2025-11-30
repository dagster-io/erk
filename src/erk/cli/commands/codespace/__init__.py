"""GitHub Codespaces integration for remote planning."""

import click

from erk.cli.commands.codespace.configure_cmd import configure_codespace
from erk.cli.commands.codespace.connect_cmd import connect_codespace
from erk.cli.commands.codespace.create_cmd import create_codespace
from erk.cli.commands.codespace.init_cmd import init_codespace
from erk.cli.commands.codespace.list_cmd import list_codespaces
from erk.cli.commands.codespace.plan_cmd import plan_codespace
from erk.cli.commands.codespace.register_cmd import register_codespace
from erk.cli.commands.codespace.unregister_cmd import unregister_codespace


@click.group("codespace")
def codespace_group() -> None:
    """GitHub Codespaces integration for remote planning."""
    pass


codespace_group.add_command(configure_codespace, name="configure")
codespace_group.add_command(connect_codespace, name="connect")
codespace_group.add_command(create_codespace, name="create")
codespace_group.add_command(init_codespace, name="init")
codespace_group.add_command(list_codespaces, name="list")
codespace_group.add_command(plan_codespace, name="plan")
codespace_group.add_command(register_codespace, name="register")
codespace_group.add_command(unregister_codespace, name="unregister")
