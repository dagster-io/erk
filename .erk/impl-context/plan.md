# Add a print statement to the first Python file

## Context

The task is to add a print statement to the first Python file encountered in the project. The first Python file in the source tree is `src/erk/__init__.py`, which is the CLI entry point module.

## Changes

### Modify `src/erk/__init__.py`

Add a `print()` statement at the top of the file, after the module docstring and before the import. The print statement should be a simple hello-world style message.

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

**After modification:**

```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

print("Hello from erk!")

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

The print statement is placed after the docstring and before the import, as a module-level statement that will execute when the module is first imported.

## Files NOT changing

- No other files are modified
- No tests are added (this is a trivial one-line addition)
- No configuration files change

## Verification

After making the change, verify:

1. The file parses correctly: run `python -c "import ast; ast.parse(open('src/erk/__init__.py').read())"` or use `ty` to check
2. Run `ruff check src/erk/__init__.py` to ensure no lint violations