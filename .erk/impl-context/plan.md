# Add print statement to first Python file

## Context

The prompt asks to add a print statement to the first Python file found in the codebase. The first Python file in the main source tree is `src/erk/__init__.py`, which is the CLI entry point for the erk package.

## Changes

### Modify `src/erk/__init__.py`

Add a `print()` statement at the top level of the module. Place it after the docstring and import, before the `main()` function definition.

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

**Change:** Add `print("hello")` on a new line after the import and before the `main()` function:

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

## Files NOT changing

- No other files are modified
- No tests are added or changed
- No configuration changes

## Verification

After making the change, verify:
1. The file is syntactically valid Python (`python -c "import ast; ast.parse(open('src/erk/__init__.py').read())"`)
2. Existing tests still pass (run `pytest`)