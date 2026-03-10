"""Machine-readable JSON repo commands (erk json repo ...)."""

import click

from erk.cli.commands.repo.check.json_cli import json_repo_check


@click.group("repo")
def json_repo_group() -> None:
    """Machine-readable repo commands."""
    pass


json_repo_group.add_command(json_repo_check, name="check")
