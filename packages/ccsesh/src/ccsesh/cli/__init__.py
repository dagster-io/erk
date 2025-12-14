"""Static CLI definition for ccsesh.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

import click

from ccsesh.commands.project import project
from ccsesh.commands.session import session

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(name="ccsesh", context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """Claude Code session inspection tools."""
    pass


cli.add_command(project)
cli.add_command(session)
