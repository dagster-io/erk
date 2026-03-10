"""Top-level machine command group."""

import click

from erk.cli.commands.json.one_shot_cmd import json_one_shot
from erk.cli.commands.json.pr_group import json_pr_group


@click.group("json")
def json_group() -> None:
    """Machine-facing command tree."""


json_group.add_command(json_one_shot, name="one-shot")
json_group.add_command(json_pr_group, name="pr")
