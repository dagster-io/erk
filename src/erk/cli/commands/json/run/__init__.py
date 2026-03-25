"""Machine-readable JSON workflow run commands (erk json run ...)."""

import click

from erk.cli.commands.run.list_json_cli import json_workflow_run_list
from erk.cli.commands.run.logs_json_cli import json_workflow_run_logs
from erk.cli.commands.run.status_json_cli import json_workflow_run_status


@click.group("run")
def json_run_group() -> None:
    """Machine-readable workflow run commands."""
    pass


json_run_group.add_command(json_workflow_run_list, name="list")
json_run_group.add_command(json_workflow_run_status, name="status")
json_run_group.add_command(json_workflow_run_logs, name="logs")
