"""Machine-facing `erk json pr ...` commands."""

import click

from erk.cli.commands.json.pr_list_cmd import json_pr_list
from erk.cli.commands.json.pr_view_cmd import json_pr_view


@click.group("pr")
def json_pr_group() -> None:
    """Machine-facing plan commands."""


json_pr_group.add_command(json_pr_list, name="list")
json_pr_group.add_command(json_pr_view, name="view")
