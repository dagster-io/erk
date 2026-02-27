# Add Print Statement to First Python File

## Context

Add a print statement to the first Python file found in the codebase. The first Python file in the main source tree is `src/erk/__init__.py`, which is the CLI entry point module.

## Changes

### Modify `src/erk/__init__.py`

Add a `print()` statement to the file. The print statement should be placed at module level, after the existing docstring and import, so it executes when the module is loaded.

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

**Target content:**
```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli

print("Hello from erk!")


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

Add `print("Hello from erk!")` on a new line after the `from erk.cli.cli import cli` import and before the `main()` function definition.

## Files NOT Changing

- No other files need modification
- No test files need modification
- No configuration files need modification

## Verification

After making the change, verify:
1. The file parses correctly (run `python -c "import ast; ast.parse(open('src/erk/__init__.py').read())"`)
2. Run `ruff check src/erk/__init__.py` to ensure no linting errors
3. Run `ty check src/erk/__init__.py` to ensure no type errors