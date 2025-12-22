"""JSONL viewer CLI command."""

from pathlib import Path

import click

from erk.tui.jsonl_viewer.app import JsonlViewerApp


@click.command("jsonl")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def jsonl_viewer(path: Path) -> None:
    """View a Claude Code session JSONL file in an interactive TUI.

    PATH is the path to a .jsonl file to view.

    Use Enter to expand/collapse entries, q or Esc to quit.
    """
    app = JsonlViewerApp(path)
    app.run()
