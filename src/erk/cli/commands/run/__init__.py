"""Run management commands."""

import click

from erk.cli.commands.run.cancel_cmd import cancel_run
from erk.cli.commands.run.list_cmd import list_runs
from erk.cli.commands.run.logs_cmd import logs_run
from erk.cli.commands.run.retry_cmd import retry_run


@click.group("run")
def run_group() -> None:
    """View GitHub Actions workflow runs for plan implementations."""
    pass


# Register subcommands
run_group.add_command(cancel_run)
run_group.add_command(list_runs)
run_group.add_command(logs_run)
run_group.add_command(retry_run)
