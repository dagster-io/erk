# Add print hello world to first Python file

## Context

The task is to add a `print("hello world")` statement to the first Python file found in the project source tree. The first Python file in the source tree is `src/erk/__init__.py`.

## Changes

### `src/erk/__init__.py`

Add `print("hello world")` at the top of the file, immediately after the module docstring and before the import statement.

**Current content:**
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

**New content:**
```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

print("hello world")

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

The only change is adding `print("hello world")` on line 7 (after the docstring, before the import).

## Files NOT changing

All other files in the project remain unchanged.

## Verification

After implementation, verify by running:
```bash
python -c "import erk"
```

This should print `hello world` to stdout when the module is imported.