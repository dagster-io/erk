# Add Print Statement to First Python File

## Context

The prompt asks to add a print statement to the first Python file found in the project. The first Python file in the main source directory is `src/erk/__init__.py`, which is the package entry point for the erk CLI.

## Changes

### Modify `src/erk/__init__.py`

Add a print statement to the file. The current contents are:

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

Add a `print()` statement at module level, after the imports and before the `main()` function:

```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli

print("Hello from erk")


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

The specific change is adding `print("Hello from erk")` on line 9, after the import and before the `main` function definition.

## Files NOT Changing

- No other files need modification
- No test files need changes
- No configuration files need changes

## Verification

After making the change, verify:
1. The file is valid Python syntax (run `python -c "import ast; ast.parse(open('src/erk/__init__.py').read())"`)
2. The print statement is present in the file