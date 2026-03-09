# Add Hello World to First Python File

## Context

The task is to add a "hello world" print statement to the first Python file found in the project source tree. The first Python file in `src/` is `src/erk/__init__.py`.

## Changes

### Modify `src/erk/__init__.py`

Add a `print("Hello, World!")` statement at the top of the file, after the module docstring and before the import.

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

print("Hello, World!")

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

The only change is inserting `print("Hello, World!")` on line 7 (after the docstring, before the import).

## Files NOT Changing

- No other files are modified
- No tests are added (this is a trivial one-line addition)
- No configuration changes

## Verification

After making the change, verify that:
1. `python -c "import erk"` prints "Hello, World!" to stdout
2. The existing CLI still works: `erk --help` should show help output (preceded by "Hello, World!")