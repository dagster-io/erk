"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

print("hello")

from erk.cli.cli import cli  # noqa: E402


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
