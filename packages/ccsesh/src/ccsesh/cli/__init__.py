"""Static CLI definition for ccsesh.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(name="ccsesh", context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """Claude Code session inspection tools."""
    pass


# Register commands here as they are added:
# from ccsesh.commands.example.command import example_command
# cli.add_command(example_command)
