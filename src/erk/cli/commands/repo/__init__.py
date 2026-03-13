"""Repo management commands."""

import click

from erk.cli.commands.repo.check.cli import repo_check


@click.group("repo")
def repo_group() -> None:
    """Manage remote repository configuration."""
    pass


repo_group.add_command(repo_check, name="check")
