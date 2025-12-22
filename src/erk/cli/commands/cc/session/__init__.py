"""Session management command group for Claude Code."""

import click

from erk.cli.commands.cc.session.list_cmd import list_sessions
from erk.cli.commands.cc.session.show_cmd import show_session


@click.group("session")
def session_group() -> None:
    """Manage Claude Code sessions."""


session_group.add_command(list_sessions)
session_group.add_command(show_session)
