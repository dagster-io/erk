"""GitHub Codespaces integration for remote planning."""

import click

from erk.cli.commands.codespace.init_cmd import init_codespace
from erk.cli.commands.codespace.plan_cmd import plan_codespace


@click.group("codespace")
def codespace_group() -> None:
    """GitHub Codespaces integration for remote planning."""
    pass


codespace_group.add_command(init_codespace, name="init")
codespace_group.add_command(plan_codespace, name="plan")
