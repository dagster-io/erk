"""Machine-readable JSON PR commands (erk json pr ...)."""

import click

from erk.cli.commands.pr.list.json_cli import json_pr_list
from erk.cli.commands.pr.view.json_cli import json_pr_view


@click.group("pr")
def json_pr_group() -> None:
    """Machine-readable PR commands."""
    pass


json_pr_group.add_command(json_pr_list, name="list")
json_pr_group.add_command(json_pr_view, name="view")
