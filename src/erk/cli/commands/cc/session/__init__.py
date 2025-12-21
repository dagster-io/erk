"""Session management command group for Claude Code."""

import click

from erk.cli.commands.cc.session.list_cmd import list_sessions


@click.group("session")
def session_group() -> None:
    """Manage Claude Code sessions."""


session_group.add_command(list_sessions)
