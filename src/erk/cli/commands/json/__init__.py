"""Machine (JSON-in/JSON-out) command group: erk json ..."""

import click

from erk.cli.commands.json.one_shot import json_one_shot
from erk.cli.commands.json.pr import json_pr_group


@click.group("json")
def json_group() -> None:
    """Machine-readable JSON commands for agent consumption."""
    pass


json_group.add_command(json_one_shot, name="one-shot")
json_group.add_command(json_pr_group, name="pr")
