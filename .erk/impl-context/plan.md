# Add Hello World to First Python File

## Context

The prompt asks to add a "hello world" message to the first Python file found in the codebase. The first Python source file in the project is `src/erk/__init__.py`, which serves as the CLI entry point for the erk package.

## Changes

### File: `src/erk/__init__.py`

Add a `print("Hello, World!")` statement to the file. The print should execute when the module is imported, placed after the docstring and before the existing imports.

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

The only change is adding `print("Hello, World!")` on a new line after the module docstring and before the import statement, with a blank line before and after for readability.

## Files NOT Changing

- `src/erk/__main__.py` — no changes needed
- All other files in the project — out of scope
- No test files — this is a trivial addition

## Verification

1. Run `python -c "import erk"` and confirm "Hello, World!" is printed to stdout
2. Run `erk --help` and confirm the CLI still works (the hello world message will appear before the help output)