# Add print statement to first Python file

## Context

Simple task: add a print statement to the first Python source file found in the project (`src/erk/__init__.py`).

## Target File

`src/erk/__init__.py` — the top-level package init file for erk.

Current contents:
```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

## Change

Add `print("hello")` after the module docstring and import, at module level (line 9, after the import).

```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli

print("hello")


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

## Verification

Run `python -c "import erk"` — should print `hello`.
