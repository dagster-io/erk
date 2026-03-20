"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.

The cli import is deferred to main() to avoid circular imports with
erk_slots, which imports from erk.cli.* modules.
"""


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    from erk.cli.cli import cli

    cli()
