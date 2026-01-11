"""Learn subcommand group for plan documentation learning workflow."""

import click

from erk.cli.commands.plan.learn.complete_cmd import complete_learn


@click.group("learn")
def learn_group() -> None:
    """Manage documentation learning plans."""
    pass


learn_group.add_command(complete_learn, name="complete")
