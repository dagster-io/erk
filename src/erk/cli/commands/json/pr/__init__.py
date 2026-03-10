"""Machine PR command group: erk json pr ..."""

import click

from erk.cli.commands.json.pr.list_cmd import json_pr_list
from erk.cli.commands.json.pr.view_cmd import json_pr_view


@click.group("pr")
def json_pr_group() -> None:
    """Machine-readable PR commands."""
    pass


json_pr_group.add_command(json_pr_list, name="list")
json_pr_group.add_command(json_pr_view, name="view")
