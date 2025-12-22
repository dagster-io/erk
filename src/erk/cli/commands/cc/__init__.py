"""Claude Code session tools command group."""

import click

from erk.cli.commands.cc.jsonl_cmd import jsonl_viewer
from erk.cli.commands.cc.session import session_group


@click.group("cc")
def cc_group() -> None:
    """Claude Code session tools."""


cc_group.add_command(session_group)
cc_group.add_command(jsonl_viewer)
