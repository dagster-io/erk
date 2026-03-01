"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli


# Entry point registered as console_scripts in pyproject.toml
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
