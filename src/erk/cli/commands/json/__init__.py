"""Machine-readable JSON command tree (erk json ...).

All commands in this tree accept JSON input from stdin and produce
structured JSON output. No human-facing formatting or Click options
for input — the request dataclass IS the schema.
"""

import click

from erk.cli.commands.json.objective import json_objective_group
from erk.cli.commands.json.pr import json_pr_group
from erk.cli.commands.json.repo import json_repo_group
from erk.cli.commands.one_shot.json_cli import json_one_shot


@click.group("json")
def json_group() -> None:
    """Machine-readable JSON commands."""
    pass


json_group.add_command(json_one_shot, name="one-shot")
json_group.add_command(json_objective_group, name="objective")
json_group.add_command(json_pr_group, name="pr")
json_group.add_command(json_repo_group, name="repo")
