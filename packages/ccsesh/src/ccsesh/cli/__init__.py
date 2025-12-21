"""Static CLI definition for ccsesh.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

from pathlib import Path

import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class CcseshContext:
    """Context object for ccsesh CLI commands."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd


pass_context = click.make_pass_decorator(CcseshContext)


@click.group(name="ccsesh", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Claude Code session inspection tools."""
    ctx.obj = CcseshContext(cwd=Path.cwd())


# Register commands here as they are added:
# from ccsesh.commands.example.command import example_command
# cli.add_command(example_command)
