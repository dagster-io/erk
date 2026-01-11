"""Learn subcommand group for plan documentation learning workflow."""

import click

from erk.cli.commands.plan.learn.complete_cmd import complete_learn
from erk.cli.commands.plan.learn.create_raw_cmd import create_raw


@click.group("learn")
def learn_group() -> None:
    """Manage documentation learning plans."""
    pass


learn_group.add_command(complete_learn, name="complete")
learn_group.add_command(create_raw, name="raw")
